"""DB-freie Tests für das CSV→Lead-Mapping (services/lead_csv_import.py)."""
from app.scripts.backfill_lead_notes_fields import extract_from_notes
from app.services.lead_csv_import import (
    build_notes,
    normalize_header,
    parse_employee_count,
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
        # Geschäftsführung/Mitarbeiterzahl haben eigene Felder → NICHT in den
        # Notizen (siehe TestEmployeeCountAndDecisionMaker).
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


class TestEmployeeCountAndDecisionMaker:
    def test_mapped_as_own_fields(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        f = row_to_lead_fields(PROJEKTRON_ROW, cm, target="x", source="s")
        assert f["employee_count"] == 20
        assert f["decision_maker"] == "Manfred Schüller"

    def test_no_longer_folded_into_notes(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        f = row_to_lead_fields(PROJEKTRON_ROW, cm, target="x", source="s")
        assert "Mitarbeiter:" not in (f["notes"] or "")
        assert "Geschäftsführung:" not in (f["notes"] or "")

    def test_parse_variants(self):
        assert parse_employee_count("20") == 20
        assert parse_employee_count("ca. 1.500") == 1500
        assert parse_employee_count("50-100") == 50      # untere Grenze
        assert parse_employee_count("19028") == 19028

    def test_parse_rejects_unusable(self):
        for bad in (None, "", "   ", "unbekannt", "k.A."):
            assert parse_employee_count(bad) is None

    def test_unparseable_value_stays_in_notes(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        row = {**PROJEKTRON_ROW, "Mitarbeiterzahl (ca.)": "unbekannt"}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["employee_count"] is None
        assert "Mitarbeiter: unbekannt" in f["notes"]   # nichts geht verloren

    def test_empty_fields_are_none(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        row = {**PROJEKTRON_ROW, "Mitarbeiterzahl (ca.)": "", "Geschäftsführung": ""}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["employee_count"] is None and f["decision_maker"] is None

    def test_decision_maker_independent_of_contact(self):
        # 92 Projektron-Leads haben eine GF, aber KEINEN Ansprechpartner
        cm = resolve_columns(PROJEKTRON_HEADERS)
        row = {**PROJEKTRON_ROW, "Ansprechpartner (Referenz)": "", "Position": ""}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["contact_name"] is None
        assert f["decision_maker"] == "Manfred Schüller"


class TestCityFallback:
    def test_uses_second_city_column_when_primary_empty(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        assert cm["city_fallback"] == "Ort (Projektron-Profil)"
        row = {**PROJEKTRON_ROW, "Ort (Impressum)": "", "Ort (Projektron-Profil)": "München"}
        f = row_to_lead_fields(row, cm, target="x", source="s")
        assert f["address"] == "Nordostpark 102, 90411 München"

    def test_primary_wins_when_present(self):
        cm = resolve_columns(PROJEKTRON_HEADERS)
        f = row_to_lead_fields(PROJEKTRON_ROW, cm, target="x", source="s")
        assert "Nürnberg" in f["address"]


class TestBackfillFromNotes:
    def test_extracts_both_and_cleans(self):
        notes = "Kurzname: A2\nGeschäftsführung: Manfred Schüller\nMitarbeiter: 20\nHR: HRB 37520"
        emp, dec, cleaned = extract_from_notes(notes)
        assert emp == 20
        assert dec == "Manfred Schüller"
        assert "Mitarbeiter:" not in cleaned and "Geschäftsführung:" not in cleaned
        assert "Kurzname: A2" in cleaned and "HR: HRB 37520" in cleaned

    def test_noop_when_nothing_to_extract(self):
        notes = "Kurzname: A2\nHR: HRB 37520"
        assert extract_from_notes(notes) == (None, None, notes)
        assert extract_from_notes(None) == (None, None, None)

    def test_vorstand_counts_as_decision_maker(self):
        emp, dec, _ = extract_from_notes("Vorstand: Dr. Sven Kleiner")
        assert dec == "Dr. Sven Kleiner" and emp is None

    def test_unparseable_employee_line_is_kept(self):
        emp, _, cleaned = extract_from_notes("Mitarbeiter: unbekannt\nHR: X")
        assert emp is None
        assert "Mitarbeiter: unbekannt" in cleaned   # Zeile bleibt stehen

    def test_only_one_line_removed_each(self):
        emp, dec, cleaned = extract_from_notes("Mitarbeiter: 5\nSonstiges: Mitarbeiter: 9")
        assert emp == 5
        assert "Sonstiges: Mitarbeiter: 9" in cleaned


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
