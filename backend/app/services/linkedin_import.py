"""Parser für LinkedIns offiziellen Datenexport.

Quelle: LinkedIn → Einstellungen → Datenschutz → "Kopie deiner Daten
anfordern". Kostenlos, keine API, ToS-konform (eigener DSGVO-Datenexport).

Unterstützt beides:
- die einzelne `Connections.csv`
- das komplette ZIP-Archiv (wird IN-MEMORY entpackt) — daraus werden
  zusätzlich `Invitations.csv` (offene ausgehende Kontaktanfragen →
  Status-Vorschlag "contacted") und `messages.csv` (Nachrichtenverlauf →
  Status-Vorschlag "in_conversation" + erledigte Aktivitäten) gezogen.

Format-Eigenheiten, die hier abgefangen werden:
- Connections.csv beginnt oft mit einem "Notes:"-Vorspann (1–3 Zeilen
  Hinweistext) VOR der eigentlichen Header-Zeile.
- Header sind je nach Account-Sprache englisch ODER deutsch
  ("First Name"/"Vorname", "Connected On"/"Verbunden am", …).
- E-Mail ist meist leer (Kontakte müssen Export explizit erlauben).
- UTF-8, teils mit BOM.
"""
import csv
import io
import zipfile

# Zip-Bomb-Guards für das Archiv (der echte Export ist < 1 MB)
_ZIP_MAX_ENTRIES = 200
_ZIP_MAX_UNCOMPRESSED = 100 * 1024 * 1024  # 100 MB
_ZIP_MAX_MEMBER = 50 * 1024 * 1024  # 50 MB pro Datei

# Pro Lead höchstens so viele Nachrichten als Aktivitäten übernehmen
MAX_MESSAGES_PER_LEAD = 20
_MESSAGE_SNIPPET_LEN = 300

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


def normalize_profile_url(url: str | None) -> str:
    """Profil-URL auf vergleichbaren Kern reduzieren (Protokoll/www/Slash weg)."""
    u = (url or "").strip().rstrip("/").lower()
    for prefix in ("https://", "http://", "www."):
        u = u.removeprefix(prefix)
    return u


def parse_invitations(text: str) -> list[dict]:
    """Parst Invitations.csv → nur AUSGEHENDE Anfragen.
    Rückgabe: {name, url, sent_at, message} — der Abgleich, ob die Anfrage
    noch offen ist (nicht in Connections), passiert beim Zusammenführen."""
    text = text.lstrip("﻿")
    rows: list[dict] = []
    for raw in csv.DictReader(io.StringIO(text)):
        if (raw.get("Direction") or "").strip().upper() != "OUTGOING":
            continue
        name = (raw.get("To") or "").strip()
        url = (raw.get("inviteeProfileUrl") or "").strip()
        if not name and not url:
            continue
        rows.append({
            "name": name,
            "url": url,
            "sent_at": (raw.get("Sent At") or "").strip(),
            "message": (raw.get("Message") or "").strip(),
        })
    return rows


def parse_messages(text: str, own_profile_hint: str = "") -> dict[str, dict]:
    """Parst messages.csv und gruppiert nach Gesprächspartner-URL.
    Eigene Nachrichten werden über die Profil-URL des häufigsten Absenders
    erkannt (Fallback: own_profile_hint). Rückgabe:
    {norm_url: {count, last_date, messages: [{date, direction, snippet}]}}"""
    text = text.lstrip("﻿")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return {}

    # Eigene URL bestimmen: der Absender, der am häufigsten vorkommt, ist
    # in einem persönlichen Export praktisch immer der Kontoinhaber.
    sender_counts: dict[str, int] = {}
    for r in rows:
        u = normalize_profile_url(r.get("SENDER PROFILE URL"))
        if u:
            sender_counts[u] = sender_counts.get(u, 0) + 1
    own = normalize_profile_url(own_profile_hint) or (
        max(sender_counts, key=lambda k: sender_counts[k]) if sender_counts else ""
    )

    partners: dict[str, dict] = {}
    for r in rows:
        sender = normalize_profile_url(r.get("SENDER PROFILE URL"))
        recipients = [
            normalize_profile_url(u)
            for u in (r.get("RECIPIENT PROFILE URLS") or "").split(";")
            if u.strip()
        ]
        direction = "gesendet" if sender == own else "erhalten"
        partner_urls = [u for u in ([sender] + recipients) if u and u != own]
        date = (r.get("DATE") or "").strip()
        content = (r.get("CONTENT") or "").strip().replace("\r\n", "\n")
        snippet = content[:_MESSAGE_SNIPPET_LEN] + ("…" if len(content) > _MESSAGE_SNIPPET_LEN else "")
        for pu in set(partner_urls):
            entry = partners.setdefault(pu, {"count": 0, "last_date": "", "messages": []})
            entry["count"] += 1
            if date > entry["last_date"]:
                entry["last_date"] = date
            if snippet:
                entry["messages"].append({"date": date, "direction": direction, "snippet": snippet})

    # Nachrichten je Partner chronologisch, auf die letzten N begrenzen
    for entry in partners.values():
        entry["messages"].sort(key=lambda m: m["date"])
        entry["messages"] = entry["messages"][-MAX_MESSAGES_PER_LEAD:]
    return partners


def parse_linkedin_archive(data: bytes) -> dict:
    """Entpackt das Export-ZIP in-memory und parst die relevanten Dateien.
    Rückgabe: {connections: [...], invitations: [...], messages: {...}}.
    Wirft ValueError bei fehlender Connections.csv oder verdächtigem Archiv."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Datei ist kein gültiges ZIP-Archiv.")

    infos = zf.infolist()
    if len(infos) > _ZIP_MAX_ENTRIES:
        raise ValueError("ZIP enthält zu viele Dateien.")
    if sum(i.file_size for i in infos) > _ZIP_MAX_UNCOMPRESSED:
        raise ValueError("ZIP-Inhalt ist zu groß.")

    def _read(name_lower: str) -> str | None:
        for info in infos:
            base = info.filename.rsplit("/", 1)[-1].lower()
            if base == name_lower and not info.is_dir():
                if info.file_size > _ZIP_MAX_MEMBER:
                    raise ValueError(f"{info.filename} ist zu groß.")
                raw = zf.read(info)
                try:
                    return raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    return raw.decode("latin-1")
        return None

    connections_text = _read("connections.csv")
    if connections_text is None:
        raise ValueError("Keine Connections.csv im Archiv gefunden.")
    connections = parse_linkedin_connections(connections_text)

    invitations_text = _read("invitations.csv")
    invitations = parse_invitations(invitations_text) if invitations_text else []

    messages_text = _read("messages.csv")
    messages = parse_messages(messages_text) if messages_text else {}

    return {"connections": connections, "invitations": invitations, "messages": messages}


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
