"""KI-Qualitätsbewertung einer Website (A2, opt-in).

Bewertet qualitative Aspekte, die technische Checks nicht erfassen (Professionalität,
Vertrauenswürdigkeit, Design, Benutzerfreundlichkeit, Conversion-Potenzial,
Zielgruppenansprache, CTA) aus dem sichtbaren Seitentext + Struktur-Signalen.

Reine Orchestrierung mit den Bausteinen der KI-Lead-Suche (`_structured`/`Usage`),
testbar mit gemocktem Client. `extract_text` und `ki_subscore` sind rein.
"""
import html as html_mod
import re

from app.services.ai_lead_agent import _structured
from app.services.ai_pricing import Usage

# Prompt-Version — bei inhaltlichen Änderungen erhöhen (Nachvollziehbarkeit in der Historie).
AI_REVIEW_VERSION = "1"

# Teil-Dimensionen der KI-Bewertung (je 0–100) → gemittelt zum `ki`-Subscore.
AI_DIMENSIONS = ("professionalitaet", "vertrauen", "design", "usability",
                 "conversion", "zielgruppe", "cta")
AI_DIMENSION_LABELS = {
    "professionalitaet": "Professionalität",
    "vertrauen": "Vertrauenswürdigkeit",
    "design": "Design & Aktualität",
    "usability": "Benutzerfreundlichkeit",
    "conversion": "Conversion-Potenzial",
    "zielgruppe": "Zielgruppenansprache",
    "cta": "Call-to-Action",
}

_SYSTEM = """Du bist ein erfahrener Web-Consultant und bewertest die QUALITATIVEN
Aspekte einer Firmen-Website — nur anhand des mitgelieferten sichtbaren Textes und
der Struktur-Signale. Du siehst kein Bild; bewerte deshalb, was aus Inhalt, Sprache,
Struktur und Aktualität ableitbar ist.

Bewerte jede Dimension mit 0–100 (100 = exzellent):
- professionalitaet: sprachliche/inhaltliche Qualität, Seriosität, Vollständigkeit
- vertrauen: Vertrauenssignale (Kontakt, Impressum, Referenzen, Zertifikate, Transparenz)
- design: wirkt der Auftritt aktuell/gepflegt (Hinweise: Jahresangaben, Textstil, Struktur)
- usability: Orientierung, Navigation, Verständlichkeit, Struktur der Inhalte
- conversion: führt die Seite zu einer Handlung (Anfrage/Kontakt/Angebot)
- zielgruppe: spricht sie ihre Zielgruppe klar und nutzenorientiert an
- cta: Klarheit/Auffindbarkeit konkreter Handlungsaufforderungen

Regeln:
- Sei nüchtern und konkret. Keine Höflichkeitsinflation, keine 100er ohne Grund.
- `summary`: 1–2 Sätze Gesamteindruck (deutsch, sachlich).
- `strengths`/`weaknesses`: je max. 3 kurze, konkrete Punkte (deutsch).
- Erfinde KEINE Fakten, die nicht aus dem Text hervorgehen. Fehlt eine Grundlage,
  bewerte konservativ mittig und schreibe es in die Schwächen.
- Wenn kaum Text vorliegt, sage das in `summary` und bewerte niedrig-mittig."""

_SCHEMA = {
    "type": "object",
    "properties": {
        **{d: {"type": "integer", "description": f"{AI_DIMENSION_LABELS[d]} 0-100"}
           for d in AI_DIMENSIONS},
        "summary": {"type": "string", "description": "1-2 Sätze Gesamteindruck (deutsch)."},
        "strengths": {"type": "array", "items": {"type": "string"},
                      "description": "Max. 3 konkrete Stärken (deutsch)."},
        "weaknesses": {"type": "array", "items": {"type": "string"},
                       "description": "Max. 3 konkrete Schwächen (deutsch)."},
    },
    "required": ["professionalitaet", "vertrauen", "design", "usability",
                 "conversion", "zielgruppe", "cta", "summary"],
}

_STRIP_BLOCKS = re.compile(r"<(script|style|noscript|svg)\b[^>]*>.*?</\1>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n{3,}")


def extract_text(raw_html: str, limit: int = 6000) -> str:
    """Sichtbaren Text aus HTML ziehen (rein): Skripte/Styles raus, Tags raus,
    Entities dekodiert, Whitespace normalisiert, auf `limit` Zeichen gekürzt."""
    s = _STRIP_BLOCKS.sub(" ", raw_html or "")
    s = _TAGS.sub("\n", s)
    s = html_mod.unescape(s)
    s = _WS.sub(" ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    s = _NL.sub("\n\n", s).strip()
    return s[:limit]


def ki_subscore(review: dict) -> int:
    """Mittelwert der vorhandenen Dimensionen → `ki`-Subscore 0–100 (rein)."""
    vals = []
    for d in AI_DIMENSIONS:
        v = review.get(d)
        if isinstance(v, (int, float)):
            vals.append(max(0, min(100, int(v))))
    return round(sum(vals) / len(vals)) if vals else 0


def build_context(url: str, text: str, meta: dict, technologies: list[str]) -> str:
    """Kompakter Prompt-Kontext (rein): URL, Struktur-Signale, Seitentext."""
    signals = [
        f"Impressum verlinkt: {'ja' if meta.get('has_impressum') else 'nein'}",
        f"Datenschutzerklärung verlinkt: {'ja' if meta.get('has_privacy') else 'nein'}",
        f"Cookie-Banner erkannt: {'ja' if meta.get('has_cookie_banner') else 'nein'}",
        f"Ladezeit: {round((meta.get('load_time_ms') or 0) / 1000, 1)}s",
    ]
    if technologies:
        signals.append("Erkannte Technologien: " + ", ".join(technologies))
    return (f"URL: {url}\n\nStruktur-Signale:\n- " + "\n- ".join(signals)
            + f"\n\nSichtbarer Seitentext (gekürzt):\n{text or '(kein Text extrahierbar)'}")


async def review_website(ai, model: str, url: str, text: str, meta: dict,
                         technologies: list[str], usage: Usage) -> dict:
    """Führt die KI-Bewertung durch. Rückgabe: {score, dimensions, summary,
    strengths, weaknesses, version}."""
    result = await _structured(
        ai, model, _SYSTEM, build_context(url, text, meta, technologies),
        tool_name="review_website", schema=_SCHEMA, usage=usage, max_tokens=1200,
    )
    dims = [{"key": d, "label": AI_DIMENSION_LABELS[d],
             "score": max(0, min(100, int(result.get(d) or 0)))}
            for d in AI_DIMENSIONS if result.get(d) is not None]
    return {
        "score": ki_subscore(result),
        "dimensions": dims,
        "summary": str(result.get("summary") or "").strip(),
        "strengths": [str(x).strip() for x in (result.get("strengths") or [])][:3],
        "weaknesses": [str(x).strip() for x in (result.get("weaknesses") or [])][:3],
        "version": AI_REVIEW_VERSION,
    }
