"""Unit tests für die Google-ID-Token-Claims-Validierung (DB-frei).
Die Signatur-Prüfung übernimmt google-auth — hier die App-seitigen Checks."""
import pytest

from app.auth import validate_google_claims

CLIENT_ID = "12345-abc.apps.googleusercontent.com"


def _claims(**over) -> dict:
    base = {
        "aud": CLIENT_ID,
        "iss": "https://accounts.google.com",
        "email": "MartinPaush@gmail.com",
        "email_verified": True,
    }
    base.update(over)
    return base


def test_valid_claims_return_normalized_email():
    assert validate_google_claims(_claims(), CLIENT_ID) == "martinpaush@gmail.com"


def test_iss_without_scheme_is_accepted():
    assert validate_google_claims(_claims(iss="accounts.google.com"), CLIENT_ID)


def test_wrong_audience_rejected():
    with pytest.raises(ValueError):
        validate_google_claims(_claims(aud="anderer-client"), CLIENT_ID)


def test_wrong_issuer_rejected():
    with pytest.raises(ValueError):
        validate_google_claims(_claims(iss="https://evil.example.com"), CLIENT_ID)


def test_unverified_email_rejected():
    with pytest.raises(ValueError):
        validate_google_claims(_claims(email_verified=False), CLIENT_ID)


def test_missing_email_rejected():
    with pytest.raises(ValueError):
        validate_google_claims(_claims(email=""), CLIENT_ID)
