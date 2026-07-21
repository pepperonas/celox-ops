"""Reines CSV→Lead-Mapping (DB-frei, testbar).

Bildet beliebige (v. a. deutschsprachige) Firmen-CSVs auf die STABILEN Lead-Felder
ab — es wird nie das Schema pro Quelle erweitert. Standard-Spalten (Firma, E-Mail,
Telefon, Website, Adresse, Branche, Ansprechpartner, Position) werden per
Header-Heuristik erkannt; reiche Zusatzspalten (Geschäftsführung, Mitarbeiterzahl,
Handelsregister, USt-ID, „Kunde seit" …) werden in `notes` gefaltet.

Der DB-Teil (Dedup, E-Mail-Prüfung, Insert) liegt im CLI-Skript
`app.scripts.import_leads_csv`, das diese reinen Funktionen orchestriert.
"""
import re

# Kanonisches Feld -> Header-Schlüsselwörter (auf normalisierten Headern geprüft).
# Erste passende Spalte gewinnt (daher Reihenfolge in der CSV relevant, z. B.
# „Ort (Impressum)" vor „Ort (Projektron-Profil)").
_FIELD_KEYWORDS: dict[str, list[str]] = {
    "company": ["firma", "unternehmen", "company", "firmenname", "name"],
    "contact_name": ["ansprechpartner", "kontakt", "contact", "name kontakt"],
    "role": ["position", "rolle", "funktion", "titel", "title"],
    "phone": ["telefon", "tel", "phone", "rufnummer"],
    "email": ["e-mail", "email", "mail", "e mail"],
    "website": ["website", "webseite", "web", "url", "homepage", "internet"],
    "street": ["strasse", "straße", "strase", "adresse", "anschrift", "street"],
    "plz": ["plz", "postleitzahl", "postal", "zip"],
    "city": ["ort", "stadt", "city", "sitz"],
    "branche": ["branche", "branchen", "industrie", "industry", "sektor"],
}

# Zusatzspalten, die (falls vorhanden) mit deutschem Label in `notes` landen.
# key = normalisiertes Header-Fragment, value = Anzeige-Label.
_NOTE_FIELDS: list[tuple[str, str]] = [
    ("geschaftsfuhrung", "Geschäftsführung"),
    ("vorstand", "Vorstand"),
    ("mitarbeiterzahl", "Mitarbeiter"),
    ("handelsregister", "HR"),
    ("registergericht", "Registergericht"),
    ("ust-id", "USt-ID"),
    ("umsatzsteuer", "USt-ID"),
    ("kunde seit", "Kunde seit"),
    ("kurzname", "Kurzname"),
    ("referenz-url", "Referenz"),
]


def normalize_header(header: str) -> str:
    """Header → Vergleichsform: klein, ohne Klammer-Zusätze (Referenz)/(ca.),
    Umlaute simpel gefoldet, Sonderzeichen zu Leerraum, kollabiert."""
    h = (header or "").strip().lower().lstrip("﻿")
    h = re.sub(r"\([^)]*\)", " ", h)  # (Impressum), (ca.), (Referenz) entfernen
    h = h.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    h = re.sub(r"[^a-z0-9-]+", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def resolve_columns(headers: list[str]) -> dict[str, str]:
    """Ordnet kanonische Feldnamen den ORIGINAL-Headern zu (erste passende Spalte
    gewinnt). Rückgabe enthält nur gefundene Felder."""
    norm = [(orig, normalize_header(orig)) for orig in headers]
    colmap: dict[str, str] = {}
    for field, keywords in _FIELD_KEYWORDS.items():
        for orig, n in norm:
            if orig in colmap.values():
                continue
            # exakte Übereinstimmung ODER Wortgrenze (verhindert, dass „name" jede
            # Spalte mit „…name…" fängt: nur wenn das Keyword als ganzes Wort vorkommt)
            if any(n == kw or re.search(rf"(^| ){re.escape(kw)}( |$)", n) for kw in keywords):
                colmap[field] = orig
                break
    return colmap


def _compose_address(row: dict, colmap: dict[str, str]) -> str | None:
    street = (row.get(colmap.get("street", ""), "") or "").strip()
    plz = (row.get(colmap.get("plz", ""), "") or "").strip()
    city = (row.get(colmap.get("city", ""), "") or "").strip()
    plz_city = " ".join(p for p in (plz, city) if p).strip()
    parts = [p for p in (street, plz_city) if p]
    return ", ".join(parts) if parts else None


def _split_tags(value: str | None) -> list[str]:
    if not value:
        return []
    # Branchen sind kommasepariert; „&"/„und" innerhalb einer Branche bleiben.
    return [t.strip() for t in re.split(r"[,;/]| und ", value) if t.strip()]


def build_notes(row: dict, used_headers: set[str], base_target: str | None) -> str | None:
    """Faltet reiche Zusatzspalten (die kein Lead-Feld haben) in einen kompakten
    Notiz-Block. `used_headers` = bereits gemappte Spalten (werden übersprungen)."""
    lines: list[str] = []
    seen_labels: set[str] = set()
    for header, value in row.items():
        if header in used_headers:
            continue
        val = (value or "").strip()
        if not val:
            continue
        n = normalize_header(header)
        for frag, label in _NOTE_FIELDS:
            if frag in n and label not in seen_labels:
                lines.append(f"{label}: {val}")
                seen_labels.add(label)
                break
    return "\n".join(lines) if lines else None


def row_to_lead_fields(
    row: dict, colmap: dict[str, str], *, target: str | None, source: str,
) -> dict | None:
    """Eine CSV-Zeile → Lead-Feld-Dict. None, wenn keine Firma erkennbar
    (unbrauchbare Zeile). `tags` enthält die Branchen; `notes` die Zusatzfelder."""
    def col(field: str) -> str | None:
        header = colmap.get(field)
        if not header:
            return None
        v = (row.get(header, "") or "").strip()
        return v or None

    company = col("company")
    if not company:
        return None

    tags = _split_tags(col("branche"))
    used = {h for h in colmap.values()}
    notes = build_notes(row, used, target)

    fields = {
        "company": company[:255],
        "contact_name": (col("contact_name") or None),
        "role": (col("role") or None),
        "phone": (col("phone") or None),
        "email": (col("email") or None),
        "website": (col("website") or None),
        "address": _compose_address(row, colmap),
        "tags": tags or None,
        "target": (target.strip() or None) if target else None,
        "source": source,
        "notes": notes,
    }
    # Länderabhängige Feldlängen respektieren (Schema: role/website begrenzt).
    if fields["role"]:
        fields["role"] = fields["role"][:255]
    if fields["website"]:
        fields["website"] = fields["website"][:500]
    if fields["contact_name"]:
        fields["contact_name"] = fields["contact_name"][:255]
    return fields
