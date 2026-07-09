"""Parser für LinkedIns offiziellen Kontakte-Export (Connections.csv).

Quelle: LinkedIn → Einstellungen → Datenschutz → "Kopie deiner Daten
anfordern" → Connections. Kostenlos, keine API, ToS-konform (eigener
DSGVO-Datenexport).

Format-Eigenheiten, die hier abgefangen werden:
- Die Datei beginnt oft mit einem "Notes:"-Vorspann (1–3 Zeilen Hinweistext
  über fehlende E-Mails) VOR der eigentlichen Header-Zeile.
- Header sind je nach Account-Sprache englisch ODER deutsch
  ("First Name"/"Vorname", "Connected On"/"Verbunden am", …).
- E-Mail ist meist leer (Kontakte müssen Export explizit erlauben).
- UTF-8, teils mit BOM.
"""
import csv
import io

# Header-Synonyme (lowercase) → kanonischer Feldname
_HEADER_MAP = {
    "first name": "first_name",
    "vorname": "first_name",
    "last name": "last_name",
    "nachname": "last_name",
    "url": "url",
    "profil-url": "url",
    "email address": "email",
    "e-mail-adresse": "email",
    "email": "email",
    "company": "company",
    "unternehmen": "company",
    "firma": "company",
    "position": "position",
    "connected on": "connected_on",
    "verbunden am": "connected_on",
}

# Eine Zeile gilt als Header, wenn sie Vor- UND Nachname-Spalte enthält.
_REQUIRED_HEADER_KEYS = ({"first name", "last name"}, {"vorname", "nachname"})


def _find_header_line(lines: list[str]) -> int | None:
    """Index der Header-Zeile — überspringt den 'Notes:'-Vorspann."""
    for i, line in enumerate(lines[:20]):  # Vorspann ist kurz; nicht die ganze Datei scannen
        cols = {c.strip().strip('"').lower() for c in line.split(",")}
        for required in _REQUIRED_HEADER_KEYS:
            if required <= cols:
                return i
    return None


def parse_linkedin_connections(text: str) -> list[dict]:
    """Parst den CSV-Text zu Zeilen-Dicts mit kanonischen Keys
    (first_name/last_name/url/email/company/position/connected_on).
    Wirft ValueError, wenn keine Connections-Header-Zeile gefunden wird.
    Zeilen ohne jeglichen Namen werden verworfen."""
    text = text.lstrip("﻿")
    lines = text.splitlines()
    header_idx = _find_header_line(lines)
    if header_idx is None:
        raise ValueError(
            "Keine LinkedIn-Connections-Header-Zeile gefunden "
            "(erwartet Spalten wie 'First Name'/'Vorname')."
        )

    reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))
    rows: list[dict] = []
    for raw in reader:
        row = {"first_name": "", "last_name": "", "url": "", "email": "",
               "company": "", "position": "", "connected_on": ""}
        for key, value in raw.items():
            canonical = _HEADER_MAP.get((key or "").strip().lower())
            if canonical:
                row[canonical] = (value or "").strip()
        if not row["first_name"] and not row["last_name"]:
            continue  # Leer-/Trennzeilen
        rows.append(row)
    return rows


def row_to_lead_fields(row: dict) -> dict:
    """Mappt eine geparste CSV-Zeile auf RainmakerLead-Felder.
    company ist NOT NULL — Kontakte ohne Firma bekommen den Personennamen
    als Firmenname (Freiberufler/Privatkontakte)."""
    contact_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
    company = (row.get("company") or "").strip() or contact_name
    notes = None
    if row.get("connected_on"):
        notes = f"LinkedIn-Kontakt seit {row['connected_on']}"
    return {
        "company": company[:255],
        "contact_name": contact_name[:255] or None,
        "role": (row.get("position") or "").strip()[:255] or None,
        "email": (row.get("email") or "").strip()[:255] or None,
        "website": (row.get("url") or "").strip()[:500] or None,
        "source": "LinkedIn-Import",
        "notes": notes,
        "tags": ["linkedin"],
    }
