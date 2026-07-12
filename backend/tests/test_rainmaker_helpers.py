"""Unit tests für die reinen Helfer des Rainmaker-Routers (DB-frei):
LinkedIn-Zeitstempel-Parsing und URL-/Namens-Normalisierung der
Duplikat-Erkennung."""
from datetime import timezone

from app.routers.rainmaker import _norm_url, _parse_linkedin_datetime, _row_keys


def test_parse_linkedin_datetime_valid():
    dt = _parse_linkedin_datetime("2026-07-08 23:03:13 UTC")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 7, 8, 23)


def test_parse_linkedin_datetime_invalid_returns_none():
    assert _parse_linkedin_datetime("kein datum") is None
    assert _parse_linkedin_datetime("") is None
    assert _parse_linkedin_datetime(None) is None
    # Falsches Format (US-Datum aus Invitations.csv) → None statt Crash
    assert _parse_linkedin_datetime("7/8/26, 3:43 PM") is None


def test_norm_url_strips_protocol_www_and_slash():
    assert _norm_url("https://www.linkedin.com/in/max/") == "linkedin.com/in/max"
    assert _norm_url("http://linkedin.com/in/max") == "linkedin.com/in/max"
    assert _norm_url("LinkedIn.com/in/Max") == "linkedin.com/in/max"


def test_norm_url_empty_is_none():
    assert _norm_url(None) is None
    assert _norm_url("") is None
    assert _norm_url("   ") is None


def test_row_keys_name_is_lowercased_and_trimmed():
    url_key, name_key = _row_keys("Max", "Mustermann", "https://www.linkedin.com/in/max")
    assert url_key == "linkedin.com/in/max"
    assert name_key == "max mustermann"
    # Ohne URL: nur Namens-Key
    url_key, name_key = _row_keys("Erika", "", "")
    assert url_key is None
    assert name_key == "erika"
