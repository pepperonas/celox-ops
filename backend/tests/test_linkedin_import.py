"""Unit tests für den LinkedIn-Connections.csv-Parser (DB-frei)."""
import pytest

from app.services.linkedin_import import parse_linkedin_connections, row_to_lead_fields

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
