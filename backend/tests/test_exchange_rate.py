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
