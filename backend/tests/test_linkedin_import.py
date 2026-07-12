"""Unit tests für die LinkedIn-Export-Parser (DB-frei)."""
import io
import zipfile

import pytest

from app.services.linkedin_import import (
    normalize_profile_url,
    parse_invitations,
    parse_linkedin_archive,
    parse_linkedin_connections,
    parse_messages,
    row_to_lead_fields,
)

EN_CSV = '''Notes:
"When exporting your connection data, you may notice that some of the email addresses are missing. You will only see email addresses for connections who have allowed their connections to see or download their email address."

First Name,Last Name,URL,Email Address,Company,Position,Connected On
Max,Mustermann,https://www.linkedin.com/in/max-mustermann,,ACME GmbH,CTO,05 Mar 2024
Erika,Musterfrau,https://www.linkedin.com/in/erika,erika@example.com,"Müller, Schmidt & Co. KG",Geschäftsführerin,12 Jan 2023
Solo,Selbstständig,https://www.linkedin.com/in/solo,,,Freelancer,01 Feb 2025
'''

DE_CSV = '''Vorname,Nachname,URL,E-Mail-Adresse,Unternehmen,Position,Verbunden am
Hans,Beispiel,https://www.linkedin.com/in/hans,,Beispiel AG,Entwickler,03 Apr 2022
'''


def test_parses_english_export_with_notes_preamble():
    rows = parse_linkedin_connections(EN_CSV)
    assert len(rows) == 3
    assert rows[0]["first_name"] == "Max"
    assert rows[0]["company"] == "ACME GmbH"
    assert rows[0]["connected_on"] == "05 Mar 2024"
    # Quoted Feld mit Komma bleibt intakt
    assert rows[1]["company"] == "Müller, Schmidt & Co. KG"
    assert rows[1]["email"] == "erika@example.com"


def test_parses_german_headers_without_preamble():
    rows = parse_linkedin_connections(DE_CSV)
    assert len(rows) == 1
    assert rows[0]["last_name"] == "Beispiel"
    assert rows[0]["company"] == "Beispiel AG"
    assert rows[0]["connected_on"] == "03 Apr 2022"


def test_bom_and_blank_rows_are_handled():
    rows = parse_linkedin_connections("﻿" + EN_CSV + ",,,,,,\n")
    assert len(rows) == 3  # Leerzeile ohne Namen verworfen


def test_rejects_non_connections_csv():
    with pytest.raises(ValueError):
        parse_linkedin_connections("foo,bar\n1,2\n")


def test_lead_mapping_with_company():
    fields = row_to_lead_fields(parse_linkedin_connections(EN_CSV)[0])
    assert fields["company"] == "ACME GmbH"
    assert fields["contact_name"] == "Max Mustermann"
    assert fields["role"] == "CTO"
    assert fields["email"] is None
    assert fields["website"] == "https://www.linkedin.com/in/max-mustermann"
    assert fields["source"] == "LinkedIn-Import"
    assert fields["tags"] == ["linkedin"]
    assert "05 Mar 2024" in fields["notes"]


def test_lead_mapping_falls_back_to_person_name_as_company():
    # company ist NOT NULL — Kontakte ohne Firma bekommen den Personennamen
    fields = row_to_lead_fields(parse_linkedin_connections(EN_CSV)[2])
    assert fields["company"] == "Solo Selbstständig"
    assert fields["role"] == "Freelancer"


INVITATIONS_CSV = '''From,To,Sent At,Message,Direction,inviterProfileUrl,inviteeProfileUrl
Martin Pfeffer,Saskia Müller,"7/8/26, 3:43 PM",,OUTGOING,https://www.linkedin.com/in/martin-pfeffer-020831134,https://www.linkedin.com/in/saskia-mueller-1
Anna Bewerber,Martin Pfeffer,"7/1/26, 9:00 AM",Hallo!,INCOMING,https://www.linkedin.com/in/anna-b,https://www.linkedin.com/in/martin-pfeffer-020831134
Martin Pfeffer,Max Mustermann,"6/1/26, 1:00 PM",Hi Max,OUTGOING,https://www.linkedin.com/in/martin-pfeffer-020831134,https://www.linkedin.com/in/max-mustermann
'''

MESSAGES_CSV = '''"CONVERSATION ID","CONVERSATION TITLE","FROM","SENDER PROFILE URL","TO","RECIPIENT PROFILE URLS","DATE","SUBJECT","CONTENT","FOLDER","ATTACHMENTS"
"c1","","Martin Pfeffer","https://www.linkedin.com/in/martin-pfeffer-020831134","Erika Musterfrau","https://www.linkedin.com/in/erika","2026-07-01 10:00:00 UTC","","Hallo Erika, kurze Frage.","INBOX",""
"c1","","Erika Musterfrau","https://www.linkedin.com/in/erika","Martin Pfeffer","https://www.linkedin.com/in/martin-pfeffer-020831134","2026-07-02 11:30:00 UTC","","Gerne! Antwort folgt.","INBOX",""
"c2","","Martin Pfeffer","https://www.linkedin.com/in/martin-pfeffer-020831134","Max Mustermann","https://www.linkedin.com/in/max-mustermann","2026-06-15 08:00:00 UTC","","Hi Max!","INBOX",""
'''


def test_parse_invitations_outgoing_only():
    rows = parse_invitations(INVITATIONS_CSV)
    assert len(rows) == 2  # INCOMING wird ignoriert
    assert rows[0]["name"] == "Saskia Müller"
    assert rows[0]["sent_at"] == "7/8/26, 3:43 PM"
    assert rows[1]["message"] == "Hi Max"


def test_parse_messages_groups_by_partner_and_detects_own_profile():
    partners = parse_messages(MESSAGES_CSV)
    erika = partners[normalize_profile_url("https://www.linkedin.com/in/erika")]
    assert erika["count"] == 2
    assert erika["last_date"].startswith("2026-07-02")
    directions = [m["direction"] for m in erika["messages"]]
    assert directions == ["gesendet", "erhalten"]  # chronologisch
    max_p = partners[normalize_profile_url("https://www.linkedin.com/in/max-mustermann")]
    assert max_p["count"] == 1


def _build_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_parse_archive_combines_all_files():
    data = _build_zip({
        "Connections.csv": EN_CSV,
        "Invitations.csv": INVITATIONS_CSV,
        "messages.csv": MESSAGES_CSV,
    })
    archive = parse_linkedin_archive(data)
    assert len(archive["connections"]) == 3
    assert len(archive["invitations"]) == 2
    assert len(archive["messages"]) == 2


def test_parse_archive_requires_connections():
    with pytest.raises(ValueError):
        parse_linkedin_archive(_build_zip({"messages.csv": MESSAGES_CSV}))


def test_parse_archive_rejects_non_zip():
    with pytest.raises(ValueError):
        parse_linkedin_archive(b"kein zip")


def test_normalize_profile_url():
    assert normalize_profile_url("https://www.linkedin.com/in/max/") == "linkedin.com/in/max"
    assert normalize_profile_url("http://linkedin.com/in/max") == "linkedin.com/in/max"
    assert normalize_profile_url(None) == ""
    assert normalize_profile_url("") == ""


def _messages_csv(rows: list[tuple[str, str]]) -> str:
    """Baut eine messages.csv: Martin schreibt an Erika, (date, content)-Paare."""
    header = '"CONVERSATION ID","CONVERSATION TITLE","FROM","SENDER PROFILE URL","TO","RECIPIENT PROFILE URLS","DATE","SUBJECT","CONTENT","FOLDER","ATTACHMENTS"'
    lines = [header]
    for date, content in rows:
        lines.append(
            f'"c1","","Martin Pfeffer","https://www.linkedin.com/in/martin-x","Erika","https://www.linkedin.com/in/erika","{date}","","{content}","INBOX",""'
        )
    # Zweite Konversation, damit Martins URL als häufigster Absender erkannt wird
    lines.append(
        '"c2","","Martin Pfeffer","https://www.linkedin.com/in/martin-x","Max","https://www.linkedin.com/in/max","2026-01-01 00:00:00 UTC","","Hi","INBOX",""'
    )
    return "\n".join(lines) + "\n"


def test_message_snippet_is_truncated():
    long_text = "A" * 400
    partners = parse_messages(_messages_csv([("2026-07-01 10:00:00 UTC", long_text)]))
    erika = partners[normalize_profile_url("https://www.linkedin.com/in/erika")]
    snippet = erika["messages"][0]["snippet"]
    assert len(snippet) == 301  # 300 Zeichen + Ellipse
    assert snippet.endswith("…")


def test_messages_capped_to_latest_per_lead():
    rows = [(f"2026-06-{day:02d} 10:00:00 UTC", f"Nachricht {day}") for day in range(1, 26)]
    partners = parse_messages(_messages_csv(rows))
    erika = partners[normalize_profile_url("https://www.linkedin.com/in/erika")]
    assert erika["count"] == 25  # Zähler bleibt vollständig
    assert len(erika["messages"]) == 20  # aber nur die letzten 20 als Aktivitäten
    assert erika["messages"][0]["snippet"] == "Nachricht 6"  # die ältesten 5 gekappt
    assert erika["messages"][-1]["snippet"] == "Nachricht 25"


def test_lead_fields_are_length_capped():
    fields = row_to_lead_fields({
        "first_name": "Max",
        "last_name": "Mustermann",
        "company": "X" * 300,
        "position": "Y" * 300,
        "url": "https://www.linkedin.com/in/" + "z" * 600,
        "email": "",
        "connected_on": "",
    })
    assert len(fields["company"]) == 255
    assert len(fields["role"]) == 255
    assert len(fields["website"]) == 500
