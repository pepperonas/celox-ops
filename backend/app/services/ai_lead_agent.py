"""KI-Lead-Suche — Orchestrierung (Anthropic API).

Kostenoptimales 2-Stufen-Design (Claude nur fürs Urteilsvermögen, der Rest
deterministisch/gratis):

  Stufe A  parse_brief   — Freitext → Suchparameter (1 Claude-Call)
  Mitte    gather        — Overpass (+ opt. Web-Suche) → website_alive + MX + Dedup
  Stufe C  rank          — verifizierte Kandidaten ranken + Fit-Begründung (1 Call)

`anthropic` wird LAZY importiert (Modul lädt ohne SDK; Tests injizieren einen
Fake-Client). Alle Calls erzwingen strukturierte Ausgabe über Tool-Use, der
System-Prompt wird gecacht (5-min-Cache) → günstige Wiederholungen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.ai_pricing import DEFAULT_MODEL, Usage
from app.services.email_verifier import verify_email
from app.services.lead_dedup import norm_name, norm_website
from app.services.lead_discovery import SEGMENT_LABELS, discover_osm


@dataclass
class DiscoveryCaps:
    max_segments: int = 4
    max_cities: int = 4
    per_combo_limit: int = 300     # Overpass-Objekte je Kombi (nur ~15 % haben Website+E-Mail)
    max_candidates: int = 150      # Obergrenze für MX-/Rank-Aufwand
    max_web_uses: int = 4          # max Web-Suchen pro Lauf (Zeitbudget)


@dataclass
class AiDiscoveryResult:
    candidates: list[dict]         # verifiziert + gerankt, je mit fit_reason
    params: dict
    usage: Usage
    notes: list[str] = field(default_factory=list)


def get_client(api_key: str):
    """Lazy: erzeugt den AsyncAnthropic-Client (SDK erst hier importiert).
    Explizites Timeout, damit ein hängender Call (v. a. Websuche) fehlschlägt,
    statt endlos zu blockieren und die nginx-Frist (300s) zu reißen."""
    import anthropic
    return anthropic.AsyncAnthropic(api_key=api_key, timeout=150.0)


# Prädikat: ist ein Kandidat bereits als Lead bekannt? (aus dem Dedup-Index gebaut)
KnownFn = "Callable[[str | None, str | None, str | None], bool]"


async def _structured(ai, model: str, system: str, user: str, tool_name: str,
                      schema: dict, usage: Usage, *, max_tokens: int = 1500,
                      extra_tools: list | None = None) -> dict:
    """Ein Claude-Call mit erzwungener strukturierter Ausgabe (Tool-Use).
    System-Prompt wird gecacht. Rückgabe: das Tool-Input-Objekt (dict)."""
    tools = [{"name": tool_name, "description": f"Gib das Ergebnis strukturiert über {tool_name} zurück.",
              "input_schema": schema}]
    kwargs = dict(
        model=model, max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        tools=tools + (extra_tools or []),
        tool_choice={"type": "tool", "name": tool_name},
    )
    resp = await ai.messages.create(**kwargs)
    usage.add(getattr(resp, "usage", None))
    for block in getattr(resp, "content", []):
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return dict(block.input)
    raise ValueError("Modell lieferte kein strukturiertes Ergebnis.")


# --------------------------------------------------------------------------- #
#  Stufe A — Brief parsen
# --------------------------------------------------------------------------- #
_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {"type": "array", "items": {"type": "string"},
                     "description": "Branchen-Keys aus der erlaubten Liste, oder roher OSM-Tag 'key=value'."},
        "cities": {"type": "array", "items": {"type": "string"}, "description": "Städte/Orte."},
        "count": {"type": "integer", "description": "Gewünschte Lead-Anzahl (Default 10)."},
        "fit_criteria": {"type": "string", "description": "Worauf es dem Nutzer ankommt (Freitext)."},
        "exclude": {"type": "string", "description": "Was ausgeschlossen werden soll (z. B. Großkonzerne)."},
    },
    "required": ["segments", "cities", "count"],
}


def _parse_system() -> str:
    seg_list = "\n".join(f"- {k}: {v}" for k, v in SEGMENT_LABELS.items())
    return (
        "Du wandelst einen Freitext-Akquise-Brief in strukturierte Suchparameter um.\n"
        "Wähle passende Branchen-Keys aus dieser Liste (Mehrfach möglich):\n" + seg_list + "\n"
        "Passt nichts, gib einen rohen OSM-Tag 'key=value' an. Extrahiere Städte, die "
        "gewünschte Anzahl (Default 10), Fit-Kriterien und Ausschlüsse. Antworte nur über das Tool."
    )


async def parse_brief(ai, model: str, brief: str, usage: Usage) -> dict:
    out = await _structured(ai, model, _parse_system(), brief, "search_params", _PARSE_SCHEMA, usage, max_tokens=800)
    out.setdefault("segments", [])
    out.setdefault("cities", [])
    out["count"] = int(out.get("count") or 10)
    out.setdefault("fit_criteria", "")
    out.setdefault("exclude", "")
    return out


# --------------------------------------------------------------------------- #
#  Mitte — sammeln + verifizieren (deterministisch)
# --------------------------------------------------------------------------- #
def _cand_key(c: dict) -> str:
    return norm_website(c.get("website")) or ("n:" + (norm_name(c.get("name")) or ""))


async def gather_candidates(params: dict, http_client, caps: DiscoveryCaps,
                            notes: list[str], known=None) -> list[dict]:
    """Overpass-Kandidaten pro Segment×Stadt, dedupliziert, mit E-Mail-MX-Prüfung.
    Behält nur zustellbare (email_status valid/role). `known(email,website,name)`
    (optional) filtert bereits vorhandene Leads schon hier raus, damit bei einer
    Wiederholung FRISCHE Treffer nachrücken statt Duplikate."""
    seen: dict[str, dict] = {}
    known_skipped = 0
    for seg in (params.get("segments") or [])[:caps.max_segments]:
        for city in (params.get("cities") or [])[:caps.max_cities]:
            try:
                # Kein HTTP-Live-Check (zu viele False-Negatives) — MX-Prüfung unten ist das Gate.
                rows = await discover_osm(seg, city, caps.per_combo_limit, http_client,
                                          verify_websites=False)
            except ValueError as exc:
                notes.append(f"{seg} · {city}: {exc}")
                continue
            except Exception as exc:  # noqa: BLE001 — eine Kombi darf den Lauf nicht kippen
                notes.append(f"{seg} · {city}: {type(exc).__name__}")
                continue
            seg_label = SEGMENT_LABELS.get(seg, seg)
            for r in rows:
                if known and known(r.get("email"), r.get("website"), r.get("name")):
                    known_skipped += 1
                    continue                        # bereits als Lead → nicht erneut zeigen
                k = _cand_key(r)
                if k and k not in seen:
                    r.setdefault("segment", seg_label)  # Branche zur Identifikation
                    seen[k] = r
            if len(seen) >= caps.max_candidates:
                break
    cands = list(seen.values())[:caps.max_candidates]

    # E-Mail-MX prüfen (Qualität) + email_status anhängen; nur Zustellbare behalten.
    mx_cache: dict = {}
    verified: list[dict] = []
    for c in cands:
        ev = await verify_email(c.get("email"), mx_cache=mx_cache)
        if ev.status.value in ("valid", "role"):
            c["email_status"] = ev.status.value
            verified.append(c)
    # Erschöpfungs-Hinweis: nichts Frisches, aber Treffer waren bekannt.
    if not verified and known_skipped:
        notes.append(
            f"{known_skipped} Treffer sind bereits als Lead gespeichert — für neue "
            "Kontakte die Web-Suche aktivieren oder Stadt/Branche ändern."
        )
    return verified


# --------------------------------------------------------------------------- #
#  Web-Suche (opt-in) — zusätzliche Quellen über OSM hinaus
# --------------------------------------------------------------------------- #
_WEB_SCHEMA = {
    "type": "object",
    "properties": {
        "companies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "website": {"type": "string"},
                    "email": {"type": "string", "description": "E-Mail, z. B. aus dem Impressum."},
                    "address": {"type": "string"},
                },
                "required": ["name", "website", "email"],
            },
        },
    },
    "required": ["companies"],
}

_WEB_SYSTEM = (
    "Du recherchierst reale Firmen im Web für die Akquise. Nutze die Websuche. Gib über das "
    "Tool found_companies NUR echte Einzelfirmen zurück, die eine EIGENE Website UND eine "
    "E-Mail-Adresse haben (z. B. aus dem Impressum) — KEINE Verzeichnis-/Portal-/Vergleichsseiten. "
    "Achte auf die Fit-Kriterien und Ausschlüsse des Nutzers."
)


async def gather_web(ai, model: str, params: dict, http_client, caps: DiscoveryCaps,
                     usage: Usage, notes: list[str], known=None) -> list[dict]:
    """Web-Recherche via Claude (server-seitige Websuche) → strukturierte Firmen,
    dann deterministisch verifiziert (Website live + E-Mail-MX). Defensiv: fällt
    die Websuche aus, gibt es eine Notiz statt eines Fehlers."""
    seg = ", ".join(SEGMENT_LABELS.get(s, s) for s in (params.get("segments") or [])) or "Firmen"
    cities = ", ".join(params.get("cities") or []) or "Deutschland"
    research_prompt = (
        f"Recherchiere im Web bis zu {caps.max_candidates} echte {seg} in {cities}.\n"
        f"Fit-Kriterien: {params.get('fit_criteria') or '-'}\nAusschluss: {params.get('exclude') or '-'}\n"
        "Sammle je Firma: Name, Website, E-Mail (aus dem Impressum), Adresse. "
        "Liste am Ende ALLE gefundenen Firmen mit diesen Angaben auf. Keine Portal-/Verzeichnisseiten."
    )
    # Call 1: Websuche (server-seitig) → Recherche-Text.
    try:
        r1 = await ai.messages.create(
            model=model, max_tokens=4000,
            system=[{"type": "text", "text": _WEB_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": research_prompt}],
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": caps.max_web_uses}],
        )
    except Exception as exc:  # noqa: BLE001 — Websuche darf den Lauf nicht kippen
        notes.append(f"Web-Suche nicht verfügbar: {type(exc).__name__}")
        return []
    usage.add(getattr(r1, "usage", None))
    research = "".join(getattr(b, "text", "") for b in getattr(r1, "content", [])
                       if getattr(b, "type", None) == "text")
    if not research.strip():
        return []

    # Call 2: strukturieren (erzwungenes Tool, keine Websuche) → garantiert eine Liste.
    try:
        out = await _structured(
            ai, model,
            "Extrahiere aus dem Recherche-Text die Firmen mit Website UND E-Mail als Liste "
            "(keine Portale/Verzeichnisse).",
            research, "found_companies", _WEB_SCHEMA, usage, max_tokens=3000)
    except ValueError:
        return []
    raw: list[dict] = list(out.get("companies") or [])

    out: list[dict] = []
    mx_cache: dict = {}
    web_segment = seg if seg != "Firmen" else None  # Branche (Label) für die Tags
    for co in raw[:caps.max_candidates]:
        name = (co.get("name") or "").strip()
        website = (co.get("website") or "").strip()
        email = (co.get("email") or "").strip()
        if not (name and website and email):
            continue
        if known and known(email, website, name):
            continue                                # bereits als Lead → überspringen
        # KEIN HTTP-Live-Check (wirft aus dem Rechenzentrum zu viele echte Firmen
        # raus: 403/Timeout bei Bot-Schutz/langsamen Seiten). E-Mail-MX ist das Gate.
        ev = await verify_email(email, mx_cache=mx_cache)
        if ev.status.value not in ("valid", "role"):
            continue
        out.append({
            "name": name, "website": website, "email": email, "phone": None,
            "address": (co.get("address") or "").strip() or None,
            "source": "Web", "source_ref": None, "email_status": ev.status.value,
            "segment": web_segment,
        })
    return out


# --------------------------------------------------------------------------- #
#  Stufe C — ranken + begründen
# --------------------------------------------------------------------------- #
_RANK_SCHEMA = {
    "type": "object",
    "properties": {
        "selected": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Index aus der Kandidatenliste (0-basiert)."},
                    "fit_reason": {"type": "string", "description": "1 knapper Satz, warum passend."},
                },
                "required": ["index", "fit_reason"],
            },
        },
    },
    "required": ["selected"],
}

_RANK_SYSTEM = (
    "Du bewertest Firmen als Akquise-Leads gegen die Kriterien des Nutzers. Wähle die besten "
    "bis zur gewünschten Anzahl, gib je eine knappe Fit-Begründung (max 1 Satz). Schließe "
    "Ungeeignetes aus (z. B. Großkonzerne, wenn der Nutzer das nicht will). Nutze NUR die "
    "vorgelegten Kandidaten (per Index). Antworte nur über das Tool."
)


async def rank_candidates(ai, model: str, brief: str, params: dict,
                          cands: list[dict], usage: Usage) -> list[dict]:
    if not cands:
        return []
    lines = []
    for i, c in enumerate(cands):
        lines.append(f"[{i}] {c.get('name')} | {c.get('website')} | {c.get('email')} | {c.get('address') or '-'}")
    user = (
        f"Brief: {brief}\n\nFit-Kriterien: {params.get('fit_criteria') or '-'}\n"
        f"Ausschluss: {params.get('exclude') or '-'}\nGewünschte Anzahl: {params.get('count')}\n\n"
        "Kandidaten:\n" + "\n".join(lines)
    )
    out = await _structured(ai, model, _RANK_SYSTEM, user, "ranked", _RANK_SCHEMA, usage,
                            max_tokens=2000)
    result: list[dict] = []
    for sel in out.get("selected", []):
        idx = sel.get("index")
        if isinstance(idx, int) and 0 <= idx < len(cands):
            c = dict(cands[idx])
            c["fit_reason"] = (sel.get("fit_reason") or "").strip()
            result.append(c)
    return result[: int(params.get("count") or 10)]


# --------------------------------------------------------------------------- #
#  Orchestrierung
# --------------------------------------------------------------------------- #
async def run_ai_discovery(*, brief: str, model: str, api_key: str, http_client,
                           use_web_search: bool = False, caps: DiscoveryCaps | None = None,
                           ai=None, known=None) -> AiDiscoveryResult:
    """Vollständiger Lauf. `ai` (Anthropic-Client) ist für Tests injizierbar.
    OSM ist immer die Basis; `use_web_search` ergänzt Web-Treffer (opt-in, kostet).
    `known(email,website,name)` überspringt bereits vorhandene Leads schon beim
    Sammeln → Wiederholungen liefern frische statt duplizierter Kandidaten."""
    caps = caps or DiscoveryCaps()
    usage = Usage()
    notes: list[str] = []
    ai = ai or get_client(api_key)
    model = model or DEFAULT_MODEL

    params = await parse_brief(ai, model, brief, usage)
    cands = await gather_candidates(params, http_client, caps, notes, known=known)

    if use_web_search:
        web = await gather_web(ai, model, params, http_client, caps, usage, notes, known=known)
        seen = {_cand_key(c) for c in cands}
        for w in web:
            k = _cand_key(w)
            if k and k not in seen:
                seen.add(k)
                cands.append(w)
        cands = cands[:caps.max_candidates]

    ranked = await rank_candidates(ai, model, brief, params, cands, usage)
    return AiDiscoveryResult(candidates=ranked, params=params, usage=usage, notes=notes)
