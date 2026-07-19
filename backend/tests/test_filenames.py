"""Tests für services/filenames.py — einheitliche Download-Dateinamen."""
from types import SimpleNamespace

from app.services.filenames import customer_label, download_name, slug_name


class TestSlugName:
    def test_umlauts_transliterated(self):
        assert slug_name("Müller & Söhne GmbH") == "Mueller-Soehne-GmbH"
        assert slug_name("Straßenbau Süd") == "Strassenbau-Sued"
        assert slug_name("ÄÖÜ") == "AeOeUe"

    def test_other_diacritics_stripped(self):
        assert slug_name("Café René") == "Cafe-Rene"

    def test_header_breaking_chars_removed(self):
        # Ein rohes '"' im Firmennamen darf nie im Content-Disposition landen
        assert '"' not in slug_name('Firma "Quote" GmbH')
        assert slug_name('Firma "Quote" GmbH') == "Firma-Quote-GmbH"
        assert "/" not in slug_name("A/B Consulting")
        assert "\n" not in slug_name("Zeile1\nZeile2")

    def test_invoice_numbers_and_dates_intact(self):
        assert slug_name("CO-2026-0001") == "CO-2026-0001"
        assert slug_name("2026-07-19") == "2026-07-19"

    def test_dots_kept_for_domains(self):
        assert slug_name("example.de") == "example.de"
        assert slug_name("www.beispiel-firma.de") == "www.beispiel-firma.de"

    def test_dot_dash_mix_collapses(self):
        # "1. Mahnung" soll "1-Mahnung" werden, nicht "1.-Mahnung"
        assert slug_name("1. Mahnung") == "1-Mahnung"
        assert slug_name("Letzte Mahnung") == "Letzte-Mahnung"

    def test_collapses_and_strips(self):
        assert slug_name("  A --- B  ") == "A-B"
        assert slug_name("...") == ""
        assert slug_name("") == ""
        assert slug_name(None) == ""


class TestDownloadName:
    def test_full_pattern(self):
        assert (
            download_name("Rechnung", "Müller & Söhne GmbH", "CO-2026-0001")
            == "Rechnung_Mueller-Soehne-GmbH_CO-2026-0001.pdf"
        )

    def test_empty_parts_skipped(self):
        assert download_name("Rechnung", "", "CO-2026-0001") == "Rechnung_CO-2026-0001.pdf"
        assert download_name("Rechnung", None, "CO-2026-0001") == "Rechnung_CO-2026-0001.pdf"

    def test_custom_extension(self):
        assert download_name("DSGVO-Export", "Firma", "2026-07-19", ext="json").endswith(".json")
        assert download_name("EUeR", "2026", ext=".csv") == "EUeR_2026.csv"

    def test_all_empty_falls_back(self):
        assert download_name("", None) == "download.pdf"

    def test_timesheet_pattern(self):
        assert (
            download_name("Stundennachweis", "Beispiel GmbH", "2026-06-01", "2026-06-30")
            == "Stundennachweis_Beispiel-GmbH_2026-06-01_2026-06-30.pdf"
        )

    def test_header_safe_ascii_only(self):
        name = download_name("Angebot", 'Böse "Firma"/GmbH', "Titel: Größe & Co")
        assert name.isascii()
        for ch in '"/\\;\n':
            assert ch not in name


class TestCustomerLabel:
    def test_company_preferred(self):
        c = SimpleNamespace(company="Beispiel GmbH", name="Max Beispiel")
        assert customer_label(c) == "Beispiel GmbH"

    def test_name_fallback(self):
        assert customer_label(SimpleNamespace(company=None, name="Max Beispiel")) == "Max Beispiel"
        assert customer_label(SimpleNamespace(company="  ", name="Max Beispiel")) == "Max Beispiel"

    def test_none_customer(self):
        assert customer_label(None) == ""
