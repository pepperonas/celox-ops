"""Unit tests für die reinen Helfer des Rainmaker-Routers (DB-frei):
LinkedIn-Zeitstempel-Parsing. Die URL-/Namens-Normalisierung der Duplikat-
Erkennung ist nach `services/lead_dedup.py` gewandert (siehe test_lead_dedup.py)."""
from datetime import timezone

from app.routers.rainmaker import _parse_linkedin_datetime
from app.services.lead_dedup import norm_name, norm_website


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


def test_norm_website_strips_protocol_www_and_slash():
    assert norm_website("https://www.linkedin.com/in/max/") == "linkedin.com/in/max"
    assert norm_website("http://linkedin.com/in/max") == "linkedin.com/in/max"
    assert norm_website("LinkedIn.com/in/Max") == "linkedin.com/in/max"


def test_norm_website_empty_is_none():
    assert norm_website(None) is None
    assert norm_website("") is None
    assert norm_website("   ") is None


def test_norm_name_is_lowercased_and_trimmed():
    assert norm_name("  Max   Mustermann ") == "max mustermann"
    assert norm_name("Erika") == "erika"
    assert norm_name("") is None
