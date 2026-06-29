"""Shared test setup. Ensures required env is present and the User model is
registered, so the OwnedMixin FK (`users.id`) resolves during mapper
configuration for every DB-free unit test."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters-long")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

import app.models.user  # noqa: E402,F401 — register User (OwnedMixin FK target)
