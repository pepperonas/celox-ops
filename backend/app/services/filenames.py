"""Einheitliche, kundenindividuelle Download-Dateinamen.

Schema: ``Typ_Kunde_Kennung_Datum.ext`` — leere Teile entfallen. Jeder Teil wird
per :func:`slug_name` header-sicher gemacht (reines ASCII, keine Quotes/Spaces),
damit ``Content-Disposition: attachment; filename="…"`` nie brechen kann und
Dateinamen auf jedem OS/Mail-Client funktionieren.

Beispiele:
    download_name("Rechnung", "Müller & Söhne GmbH", "CO-2026-0001")
        → "Rechnung_Mueller-Soehne-GmbH_CO-2026-0001.pdf"
    download_name("DSGVO-Export", "Beispiel GmbH", "2026-07-19", ext="json")
        → "DSGVO-Export_Beispiel-GmbH_2026-07-19.json"
"""
import re
import unicodedata

_TRANSLIT = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
)
_NON_SAFE = re.compile(r"[^A-Za-z0-9.-]+")
_DOT_RUNS = re.compile(r"\.{2,}")
_MIXED_RUNS = re.compile(r"(?:\.-|-\.)+")  # „1. Mahnung“ → „1-Mahnung“, nicht „1.-Mahnung“
_DASH_RUNS = re.compile(r"-{2,}")


def slug_name(value: str | None) -> str:
    """Freitext → dateinamen-/header-sicherer ASCII-Slug.

    Deutsche Umlaute werden transliteriert (ä→ae …), übrige Diakritika per
    NFKD gestrippt, alles andere Unsichere wird zu ``-`` und kollabiert.
    Punkte bleiben erhalten (Domains wie ``example.de``), führende/trailing
    Trenner fallen weg.
    """
    if not value:
        return ""
    text = str(value).translate(_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = _NON_SAFE.sub("-", text)
    text = _DOT_RUNS.sub(".", text)
    text = _MIXED_RUNS.sub("-", text)
    text = _DASH_RUNS.sub("-", text)
    return text.strip("-.")


def download_name(*parts: object, ext: str = "pdf") -> str:
    """Baut ``Teil1_Teil2_….ext`` aus den nicht-leeren, geslugten Teilen.

    Sind alle Teile leer, fällt der Name auf ``download.ext`` zurück.
    """
    slugs = [s for s in (slug_name(str(p)) for p in parts if p is not None) if s]
    stem = "_".join(slugs) or "download"
    return f"{stem}.{ext.lstrip('.')}"


def customer_label(customer) -> str:
    """Anzeigename des Kunden für Dateinamen: Firma, sonst Name (wie Handoff)."""
    if customer is None:
        return ""
    return (getattr(customer, "company", None) or "").strip() or (
        getattr(customer, "name", None) or ""
    ).strip()
