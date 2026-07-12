"""Unit tests for the USD→EUR exchange service (pure parsing/plausibility —
no network, no DB). The live fetch itself is best-effort with fallback, so the
critical invariant is: never feed an implausible rate into invoice totals."""
from app.services.exchange_service import FALLBACK_USD_EUR, parse_frankfurter


def test_parses_valid_frankfurter_payload():
    payload = {"amount": 1.0, "base": "USD", "date": "2026-07-08", "rates": {"EUR": 0.87689}}
    assert parse_frankfurter(payload) == 0.87689


def test_rejects_missing_or_malformed_payload():
    assert parse_frankfurter({}) is None
    assert parse_frankfurter({"rates": {}}) is None
    assert parse_frankfurter({"rates": {"EUR": "kaputt"}}) is None
    assert parse_frankfurter(None) is None


def test_rejects_implausible_rates():
    # A broken upstream must never scale invoice amounts by orders of magnitude.
    assert parse_frankfurter({"rates": {"EUR": 92.0}}) is None
    assert parse_frankfurter({"rates": {"EUR": 0.009}}) is None
    assert parse_frankfurter({"rates": {"EUR": 0}}) is None


def test_fallback_is_sane():
    assert 0.5 <= FALLBACK_USD_EUR <= 1.5


# ── Cache-/Fallback-Verhalten von get_rate_info (mit gefaktem httpx) ──────────
import asyncio  # noqa: E402

import app.services.exchange_service as ex  # noqa: E402


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    """Ersetzt httpx.AsyncClient; zählt Aufrufe und liefert/vererbt Fehler."""
    calls = 0
    response: _FakeResponse | None = None
    error: Exception | None = None

    def __init__(self, timeout=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url):
        _FakeClient.calls += 1
        if _FakeClient.error is not None:
            raise _FakeClient.error
        return _FakeClient.response


def _reset(monkeypatch):
    ex._cache.update(rate=None, date=None, fetched_at=0.0, source="fallback")
    _FakeClient.calls = 0
    _FakeClient.error = None
    _FakeClient.response = None
    monkeypatch.setattr(ex.httpx, "AsyncClient", _FakeClient)


def test_rate_info_fetches_and_caches(monkeypatch):
    _reset(monkeypatch)
    _FakeClient.response = _FakeResponse({"date": "2026-07-08", "rates": {"EUR": 0.87689}})
    info = asyncio.run(ex.get_rate_info())
    assert info == {"rate": 0.87689, "source": "ecb", "date": "2026-07-08"}
    # Zweiter Aufruf innerhalb der TTL → kein zweiter Fetch
    asyncio.run(ex.get_rate_info())
    assert _FakeClient.calls == 1


def test_rate_info_falls_back_on_network_error(monkeypatch):
    _reset(monkeypatch)
    _FakeClient.error = ConnectionError("offline")
    info = asyncio.run(ex.get_rate_info())
    assert info["rate"] == FALLBACK_USD_EUR
    assert info["source"] == "fallback"


def test_rate_info_keeps_last_known_good(monkeypatch):
    _reset(monkeypatch)
    # Erst erfolgreich fetchen, dann TTL ablaufen lassen und Netz kappen
    _FakeClient.response = _FakeResponse({"date": "2026-07-08", "rates": {"EUR": 0.88}})
    asyncio.run(ex.get_rate_info())
    ex._cache["fetched_at"] = 0.0  # TTL künstlich abgelaufen
    _FakeClient.error = ConnectionError("offline")
    info = asyncio.run(ex.get_rate_info())
    assert info["rate"] == 0.88  # Last-Known-Good statt Konstante
    assert info["source"] == "ecb"


def test_rate_info_ignores_implausible_live_rate(monkeypatch):
    _reset(monkeypatch)
    _FakeClient.response = _FakeResponse({"date": "2026-07-08", "rates": {"EUR": 92.0}})
    info = asyncio.run(ex.get_rate_info())
    assert info["rate"] == FALLBACK_USD_EUR  # kaputter Kurs verworfen
