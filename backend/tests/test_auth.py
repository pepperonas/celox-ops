"""Unit tests for JWT auth helpers — pure logic, no DB required.
Run via: cd backend && pytest -v tests/test_auth.py
"""
import os
from datetime import timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters-long")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

from fastapi import HTTPException  # noqa: E402

from app.auth import create_access_token, verify_token  # noqa: E402


def test_token_roundtrip_preserves_sub():
    token = create_access_token({"sub": "martin"})
    assert verify_token(token)["sub"] == "martin"


def test_token_has_expiry_claim():
    payload = verify_token(create_access_token({"sub": "x"}))
    assert "exp" in payload


def test_expired_token_is_rejected():
    token = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-5))
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


def test_tampered_token_is_rejected():
    token = create_access_token({"sub": "x"})
    with pytest.raises(HTTPException):
        verify_token(token + "tampered")


def test_garbage_token_is_rejected():
    with pytest.raises(HTTPException):
        verify_token("not-a-jwt")


def test_custom_scope_claim_roundtrips():
    token = create_access_token({"sub": "x", "scope": "123456"})
    assert verify_token(token)["scope"] == "123456"
