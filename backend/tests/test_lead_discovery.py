"""Unit-Tests für die Lead-Discovery-Bausteine (netzfrei):
Overpass-Query-Bau, Ergebnis-Parsing, Tag-Auflösung, Qualitätsfilter,
URL-Normalisierung, Google-Details, Live-Website-Check."""
import asyncio

import httpx
import pytest

from app.services.lead_discovery import (
    OVERPASS_ENDPOINTS,
    SEGMENT_OSM_TAGS,
    _overpass_query,
    build_overpass_query,
    filter_live_websites,
    filter_osm_quality,
    normalize_url,
    parse_google,
    parse_overpass,
    parse_place_details,
    resolve_tags,
    website_alive,
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


# --------------------------------------------------------------------------- #
#  Datenqualität: E-Mail, URL-Normalisierung, Quality-Filter
# --------------------------------------------------------------------------- #
def test_parse_overpass_extracts_email_and_normalizes_website():
    data = {"elements": [{"type": "node", "id": 9, "tags": {
        "name": "Mail AG", "office": "lawyer",
        "contact:website": "kanzlei-mail.de",        # ohne Schema → https:// ergänzt
        "email": "info@kanzlei-mail.de; zweite@x.de"}}]}   # erste E-Mail gewinnt
    r = parse_overpass(data)[0]
    assert r["website"] == "https://kanzlei-mail.de"
    assert r["email"] == "info@kanzlei-mail.de"


def test_normalize_url():
    assert normalize_url("http://a.de/x") == "http://a.de/x"
    assert normalize_url("www.a.de") == "https://www.a.de"
    assert normalize_url("  a.de ") == "https://a.de"
    assert normalize_url("") is None
    assert normalize_url("keinhost") is None       # kein Punkt im Host
    assert normalize_url(None) is None


def test_filter_osm_quality_requires_website_and_email():
    rows = [
        {"name": "Beides", "website": "https://a.de", "email": "a@a.de"},
        {"name": "NurWeb", "website": "https://b.de", "email": None},
        {"name": "NurMail", "website": None, "email": "c@c.de"},
        {"name": "Nichts", "website": None, "email": None},
    ]
    kept = filter_osm_quality(rows)
    assert [r["name"] for r in kept] == ["Beides"]


def test_parse_google_skips_closed_business():
    data = {"results": [
        {"name": "Offen", "place_id": "p1", "business_status": "OPERATIONAL"},
        {"name": "Zu", "place_id": "p2", "business_status": "CLOSED_PERMANENTLY"},
        {"name": "TempZu", "place_id": "p3", "business_status": "CLOSED_TEMPORARILY"},
        {"name": "Unbekannt", "place_id": "p4"},   # kein Status → behalten
    ]}
    rows = parse_google(data, limit=10)
    assert [r["name"] for r in rows] == ["Offen", "Unbekannt"]
    assert rows[0]["_place_id"] == "p1"


def test_parse_place_details_extracts_and_normalizes():
    det = parse_place_details({"status": "OK", "result": {
        "website": "example-firma.de", "formatted_phone_number": "030 123",
        "business_status": "OPERATIONAL"}})
    assert det == {"website": "https://example-firma.de", "phone": "030 123",
                   "business_status": "OPERATIONAL"}


def test_parse_place_details_request_denied_raises():
    with pytest.raises(ValueError):
        parse_place_details({"status": "REQUEST_DENIED"})


def test_parse_place_details_not_found_is_empty():
    det = parse_place_details({"status": "NOT_FOUND"})
    assert det["website"] is None and det["business_status"] is None


# --------------------------------------------------------------------------- #
#  Live-Website-Check (mit gefaktem httpx-Client)
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, code): self.status_code = code


class _FakeClient:
    """head/get liefern Codes aus einer per-URL-Map; fehlt die URL → Exception."""
    def __init__(self, head_map=None, get_map=None, raise_on=()):
        self.head_map = head_map or {}
        self.get_map = get_map or {}
        self.raise_on = set(raise_on)

    async def head(self, url, **kw):
        if url in self.raise_on or url not in self.head_map:
            raise RuntimeError("no head")
        return _Resp(self.head_map[url])

    async def get(self, url, **kw):
        if url in self.raise_on or url not in self.get_map:
            raise RuntimeError("no get")
        return _Resp(self.get_map[url])


def _run(coro):
    return asyncio.run(coro)


def test_website_alive_head_ok():
    c = _FakeClient(head_map={"https://ok.de": 200})
    assert _run(website_alive("ok.de", c)) is True


def test_website_alive_head_405_falls_back_to_get():
    c = _FakeClient(head_map={"https://x.de": 405}, get_map={"https://x.de": 200})
    assert _run(website_alive("x.de", c)) is True


def test_website_alive_dead_domain():
    c = _FakeClient(raise_on={"https://tot.de"})
    assert _run(website_alive("tot.de", c)) is False


def test_website_alive_500_is_dead():
    c = _FakeClient(head_map={"https://err.de": 500})
    assert _run(website_alive("err.de", c)) is False


def test_website_alive_empty_url():
    assert _run(website_alive(None, _FakeClient())) is False


def test_filter_live_websites_drops_dead():
    rows = [
        {"name": "Lebt", "website": "https://live.de"},
        {"name": "Tot", "website": "https://dead.de"},
    ]
    c = _FakeClient(head_map={"https://live.de": 200}, raise_on={"https://dead.de"})
    kept = _run(filter_live_websites(rows, c))
    assert [r["name"] for r in kept] == ["Lebt"]


# --------------------------------------------------------------------------- #
#  Overpass-Mirror-Fallback (504-Überlastung)
# --------------------------------------------------------------------------- #
class _OResp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("POST", "https://overpass/"),
                response=httpx.Response(self.status_code))

    def json(self):
        return self._payload


class _SeqClient:
    """post() liefert der Reihe nach: dict→200+json, int→Status, Exception→raise."""
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def post(self, url, data=None):
        o = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(o, Exception):
            raise o
        if isinstance(o, int):
            return _OResp(o)
        return _OResp(200, o)


def test_overpass_falls_back_on_504():
    c = _SeqClient([504, {"elements": [{"type": "node", "id": 1, "tags": {"name": "X"}}]}])
    data = _run(_overpass_query("q", c))
    assert data["elements"][0]["tags"]["name"] == "X"
    assert c.calls == 2                      # erster 504 → zweiter Server liefert


def test_overpass_falls_back_on_timeout():
    c = _SeqClient([httpx.ConnectError("boom"), {"elements": []}])
    assert _run(_overpass_query("q", c)) == {"elements": []}
    assert c.calls == 2


def test_overpass_all_down_raises_valueerror():
    c = _SeqClient([504] * len(OVERPASS_ENDPOINTS))
    with pytest.raises(ValueError):
        _run(_overpass_query("q", c))
    assert c.calls == len(OVERPASS_ENDPOINTS)


def test_overpass_non_transient_aborts_immediately():
    c = _SeqClient([400, {"elements": []}])
    with pytest.raises(ValueError):
        _run(_overpass_query("q", c))
    assert c.calls == 1                      # 400 → sofort Abbruch, kein weiterer Server
