"""Unit-Tests für die Lead-Discovery-Bausteine (netzfrei):
Overpass-Query-Bau, Ergebnis-Parsing, Tag-Auflösung."""
import pytest

from app.services.lead_discovery import (
    SEGMENT_OSM_TAGS,
    build_overpass_query,
    parse_google,
    parse_overpass,
    resolve_tags,
)


def test_resolve_segment_tags():
    assert resolve_tags("steuerkanzlei") == SEGMENT_OSM_TAGS["steuerkanzlei"]


def test_resolve_raw_tag():
    assert resolve_tags("office=lawyer") == ["office=lawyer"]


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        resolve_tags("quatsch")


def test_build_query_contains_area_and_tags():
    q = build_overpass_query(["office=tax_advisor", "office=accountant"], "Berlin", 50)
    assert 'area["name"="Berlin"]->.a;' in q
    assert 'nwr["office"="tax_advisor"](area.a);' in q
    assert 'nwr["office"="accountant"](area.a);' in q
    assert "out center tags 50;" in q


def test_build_query_sanitizes_injection():
    # Anführungszeichen im Ort dürfen die Query nicht aufbrechen
    q = build_overpass_query(["office=it"], 'Berlin"]; out;//', 60)
    assert '"]; out;//' not in q
    assert 'area["name"="Berlin; out;//"]' in q or "Berlin" in q


def test_build_query_clamps_limit():
    assert "out center tags 200;" in build_overpass_query(["office=it"], "X", 9999)
    assert "out center tags 1;" in build_overpass_query(["office=it"], "X", 0)


def test_parse_overpass_extracts_fields():
    data = {"elements": [
        {"type": "node", "id": 1, "tags": {
            "name": "Muster Steuerberatung", "office": "tax_advisor",
            "website": "https://muster-stb.de", "phone": "+49 30 123",
            "addr:street": "Hauptstr.", "addr:housenumber": "5",
            "addr:postcode": "10115", "addr:city": "Berlin"}},
        {"type": "way", "id": 2, "tags": {"office": "tax_advisor"}},  # ohne Name → raus
    ]}
    rows = parse_overpass(data)
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "Muster Steuerberatung"
    assert r["website"] == "https://muster-stb.de"
    assert r["address"] == "Hauptstr. 5, 10115 Berlin"
    assert r["source"] == "OpenStreetMap"
    assert r["source_ref"] == "node/1"


def test_parse_overpass_dedupes_by_name():
    data = {"elements": [
        {"type": "node", "id": 1, "tags": {"name": "Doppelt GmbH"}},
        {"type": "node", "id": 2, "tags": {"name": "doppelt gmbh"}},
    ]}
    assert len(parse_overpass(data)) == 1


def test_parse_overpass_contact_website_fallback():
    data = {"elements": [{"type": "node", "id": 1, "tags": {
        "name": "Kontakt AG", "contact:website": "https://kontakt.de",
        "contact:phone": "030-999"}}]}
    r = parse_overpass(data)[0]
    assert r["website"] == "https://kontakt.de" and r["phone"] == "030-999"


def test_parse_google_request_denied_raises():
    import pytest as _pt
    with _pt.raises(ValueError):
        parse_google({"status": "REQUEST_DENIED", "error_message": "invalid key"}, 10)


def test_parse_google_zero_results_ok():
    assert parse_google({"status": "ZERO_RESULTS", "results": []}, 10) == []


def test_parse_google_limits_and_maps():
    data = {"results": [
        {"name": "A GmbH", "formatted_address": "Str. 1, Berlin", "place_id": "p1"},
        {"name": "", "formatted_address": "x"},  # ohne Name → raus
        {"name": "B GmbH", "formatted_address": "Str. 2, Berlin", "place_id": "p2"},
    ]}
    rows = parse_google(data, limit=1)
    assert len(rows) == 1 and rows[0]["name"] == "A GmbH" and rows[0]["source"] == "Google Places"
