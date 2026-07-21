"""DB-freie Tests für das CSV→Lead-Mapping (services/lead_csv_import.py)."""
from app.services.lead_csv_import import (
    build_notes,
    normalize_header,
    resolve_columns,
    row_to_lead_fields,
)
from app.services.taxonomy import TAXONOMIES, fold

# Original-Header der Projektron-Referenz-CSV (semikolon-getrennt).
PROJEKTRON_HEADERS = [
    "Firma", "Kurzname", "Branche(n)", "Ort (Impressum)", "PLZ", "Straße",
    "Ort (Projektron-Profil)", "Website", "E-Mail", "Telefon", "Geschäftsführung",
    "Mitarbeiterzahl (ca.)", "Handelsregister", "Registergericht", "USt-ID",
    "Ansprechpartner (Referenz)", "Position", "Projektron-Kunde seit",
    "Impressum-URL", "Referenz-URL", "Anreicherungs-Status",
]

PROJEKTRON_ROW = dict(zip(PROJEKTRON_HEADERS, [
    "A2 Doku GmbH", "A2 Doku", "Technische Dokumentation", "Nürnberg", "90411",
    "Nordostpark 102", "Nürnberg", "https://www.a2-doku.de", "info@a2-doku.de",
    "+49 911 580568-10", "Manfred Schüller", "20", "HRB 37520", "Registergericht",
    "DE329200987", "Manfred Schüller", "Geschäftsführer / Leiter Vertrieb",
    "2016", "https://a2-doku.de/impressum/", "https://www.projektron.de/ref/a2/", "ok",
]))


class TestNormalizeHeader:
    def test_strips_parentheticals_and_folds(self):
        assert normalize_header("Ansprechpartner (Referenz)") == "ansprechpartner"
        assert normalize_header("Mitarbeiterzahl (ca.)") == "mitarbeiterzahl"
        assert normalize_header("Straße") == "strasse"
        assert normalize_header("E-Mail") == "e-mail"

    def test_bom_stripped(self):
        assert normalize_header("﻿Firma") == "firma"


class TestResolveColumns:
    def test_projektron_schema(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        assert cm["company"] == "Firma"
        assert cm["email"] == "E-Mail"
        assert cm["phone"] == "Telefon"
        assert cm["website"] == "Website"
        assert cm["contact_name"] == "Ansprechpartner (Referenz)"
        assert cm["role"] == "Position"
        assert cm["branche"] == "Branche(n)"
        assert cm["street"] == "Straße"
        assert cm["plz"] == "PLZ"

    def test_first_matching_city_wins(self):
        # „Ort (Impressum)" steht vor „Ort (Projektron-Profil)" → Impressum gewinnt
        cm = resolve_columns(PROJEKTRON_HEADERS)
        assert cm["city"] == "Ort (Impressum)"

    def test_generic_english_headers(self):
        cm = resolve_columns(["Company", "Email", "Phone", "Website", "City"])
        assert cm["company"] == "Company"
        assert cm["email"] == "Email"
        assert cm["phone"] == "Phone"

    def test_company_not_swallowed_by_contact_name(self):
        # „name" als Keyword darf „Ansprechpartner" nicht als company greifen
        cm = resolve_columns(["Unternehmen", "Ansprechpartner"])
        assert cm["company"] == "Unternehmen"
        assert cm.get("contact_name") == "Ansprechpartner"

    def test_missing_fields_absent(self):
        cm = resolve_columns(["Firma"])
        assert cm == {"company": "Firma"}


class TestRowToLeadFields:
    def test_projektron_row_full_mapping(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        f = row_to_lead_fields(PROJEKTRON_ROW, cm, target="bcs / zeiterfassung", source="Projektron")
        assert f["company"] == "A2 Doku GmbH"
        assert f["contact_name"] == "Manfred Schüller"
        assert f["role"] == "Geschäftsführer / Leiter Vertrieb"
        assert f["email"] == "info@a2-doku.de"
        assert f["phone"] == "+49 911 580568-10"
        assert f["website"] == "https://www.a2-doku.de"
        assert f["address"] == "Nordostpark 102, 90411 Nürnberg"
        assert f["tags"] == ["Technische Dokumentation"]
        assert f["target"] == "bcs / zeiterfassung"
        assert f["source"] == "Projektron"

    def test_rich_extras_folded_into_notes(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        f = row_to_lead_fields(PROJEKTRON_ROW, cm, target="x", source="s")
        assert "Geschäftsführung: Manfred Schüller" in f["notes"]
        assert "Mitarbeiter: 20" in f["notes"]
        assert "HR: HRB 37520" in f["notes"]
        assert "USt-ID: DE329200987" in f["notes"]
        assert "Kunde seit: 2016" in f["notes"]
        # Anreicherungs-Status/Impressum-URL sind Rauschen → kein Label dafür
        assert "Status" not in f["notes"]
        assert "Impressum" not in f["notes"]

    def test_multiple_branches_split_to_tags(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        row = {**PROJEKTRON_ROW, "Branche(n)": "Automotive, IT-Dienstleistung & Beratung, Softwareentwicklung"}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["tags"] == ["Automotive", "IT-Dienstleistung & Beratung", "Softwareentwicklung"]

    def test_no_company_returns_none(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        assert row_to_lead_fields({**PROJEKTRON_ROW, "Firma": ""}, cm, target="x", source="s") is None
        assert row_to_lead_fields({**PROJEKTRON_ROW, "Firma": "   "}, cm, target="x", source="s") is None

    def test_partial_address(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        row = {**PROJEKTRON_ROW, "Straße": "", "PLZ": "", "Ort (Impressum)": "Berlin", "Ort (Projektron-Profil)": ""}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["address"] == "Berlin"

    def test_empty_optional_fields_are_none(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        row = {**PROJEKTRON_ROW, "E-Mail": "", "Telefon": "", "Branche(n)": ""}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["email"] is None and f["phone"] is None and f["tags"] is None

    def test_target_none_when_blank(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        f = row_to_lead_fields(PROJEKTRON_ROW, cm, target="  ", source="s")
        assert f["target"] is None

    def test_length_caps(self):
        cm = resolve_columns(["Firma", "Website"])
        f = row_to_lead_fields({"Firma": "X" * 400, "Website": "h" * 900}, cm, target=None, source="s")
        assert len(f["company"]) == 255
        assert len(f["website"]) == 500


class TestBuildNotes:
    def test_returns_none_when_nothing_notable(self):
        assert build_notes({"Firma": "X", "E-Mail": "a@b.de"}, {"Firma", "E-Mail"}, None) is None

    def test_skips_used_headers(self):
        row = {"Firma": "X", "Geschäftsführung": "Max"}
        assert "Geschäftsführung" in build_notes(row, {"Firma"}, None)
        assert build_notes(row, {"Firma", "Geschäftsführung"}, None) is None


class TestTargetTaxonomy:
    def test_field_registered(self):
        assert "target" in TAXONOMIES
        assert len(TAXONOMIES["target"]) >= 25

    def test_no_fold_duplicates(self):
        folded = [fold(v) for v in TAXONOMIES["target"]]
        assert len(folded) == len(set(folded))

    def test_covers_core_angles(self):
        joined = " ".join(TAXONOMIES["target"]).lower()
        assert "iso 27001" in joined
        assert "dsb" in joined or "datenschutz" in joined
        assert "bcs" in joined
