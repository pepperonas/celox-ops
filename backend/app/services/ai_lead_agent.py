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
    per_combo_limit: int = 40
    max_candidates: int = 60       # Obergrenze für Verifikations-/Rank-Aufwand
    max_web_uses: int = 5          # max Web-Suchen pro Lauf


@dataclass
class AiDiscoveryResult:
    candidates: list[dict]         # verifiziert + gerankt, je mit fit_reason
    params: dict
    usage: Usage
    notes: list[str] = field(default_factory=list)


def get_client(api_key: str):
    """Lazy: erzeugt den AsyncAnthropic-Client (SDK erst hier importiert)."""
    import anthropic
    return anthropic.AsyncAnthropic(api_key=api_key)


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
                            notes: list[str]) -> list[dict]:
    """Overpass-Kandidaten pro Segment×Stadt, dedupliziert, mit E-Mail-MX-Prüfung.
    Behält nur zustellbare (email_status valid/role). Website-Live-Check macht
    discover_osm bereits."""
    seen: dict[str, dict] = {}
    for seg in (params.get("segments") or [])[:caps.max_segments]:
        for city in (params.get("cities") or [])[:caps.max_cities]:
            try:
                rows = await discover_osm(seg, city, caps.per_combo_limit, http_client)
            except ValueError as exc:
                notes.append(f"{seg} · {city}: {exc}")
                continue
            except Exception as exc:  # noqa: BLE001 — eine Kombi darf den Lauf nicht kippen
                notes.append(f"{seg} · {city}: {type(exc).__name__}")
                continue
            for r in rows:
                k = _cand_key(r)
                if k and k not in seen:
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
    return verified


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
                           caps: DiscoveryCaps | None = None, ai=None) -> AiDiscoveryResult:
    """Vollständiger Lauf. `ai` (Anthropic-Client) ist für Tests injizierbar;
    sonst wird er aus `api_key` erzeugt. Web-Suche ist in v1 noch nicht aktiv
    (OSM-first); die Struktur ist darauf vorbereitet."""
    caps = caps or DiscoveryCaps()
    usage = Usage()
    notes: list[str] = []
    ai = ai or get_client(api_key)
    model = model or DEFAULT_MODEL

    params = await parse_brief(ai, model, brief, usage)
    cands = await gather_candidates(params, http_client, caps, notes)
    ranked = await rank_candidates(ai, model, brief, params, cands, usage)
    return AiDiscoveryResult(candidates=ranked, params=params, usage=usage, notes=notes)
