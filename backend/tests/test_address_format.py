"""Unit tests für den Anschriftenblock-Formatter (DB-frei)."""
from app.services.address_format import format_address_lines


def test_comma_separated_with_country_dropped():
    assert format_address_lines("Hauptstraße 24, 35510 Butzbach, Deutschland") == [
        "Hauptstraße 24",
        "35510 Butzbach",
    ]


def test_without_comma_splits_at_plz():
    assert format_address_lines("Hauptstraße 24 35510 Butzbach") == [
        "Hauptstraße 24",
        "35510 Butzbach",
    ]


def test_hyphenated_street_and_multiword_city():
    assert format_address_lines("Max-Planck-Straße 5a 60486 Frankfurt am Main") == [
        "Max-Planck-Straße 5a",
        "60486 Frankfurt am Main",
    ]


def test_house_number_range_stays_intact():
    assert format_address_lines("Musterweg 5-7, 12345 Berlin") == [
        "Musterweg 5-7",
        "12345 Berlin",
    ]


def test_hyphenated_city():
    assert format_address_lines("Am Markt 1, 51429 Bergisch-Gladbach") == [
        "Am Markt 1",
        "51429 Bergisch-Gladbach",
    ]


def test_foreign_country_kept():
    assert format_address_lines("Bahnhofstrasse 10, 8001 Zürich, Schweiz") == [
        "Bahnhofstrasse 10",
        "8001 Zürich",
        "Schweiz",
    ]


def test_multiline_input_passthrough():
    assert format_address_lines("Hauptstraße 24\n35510 Butzbach") == [
        "Hauptstraße 24",
        "35510 Butzbach",
    ]


def test_no_plz_stays_single_line():
    assert format_address_lines("Irgendwo im Nirgendwo") == ["Irgendwo im Nirgendwo"]


def test_empty_and_none():
    assert format_address_lines(None) == []
    assert format_address_lines("   ") == []
