"""Smoke tests — verify critical paths import + execute without crashing.
These do NOT require a running DB. Run via: cd backend && pytest -v
"""
import os

# Set required env BEFORE importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters-long")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")


def test_config_loads():
    from app.config import settings
    assert settings.JWT_SECRET
    assert len(settings.JWT_SECRET) >= 32


def test_all_routers_import():
    from app.routers import (
        attachments, contracts, customers, dashboard, documents, email_templates,
        euer, expenses, github, ical, invoices, leads, orders, pagespeed, search,
        time_entries, token_tracker,
    )
    assert all(hasattr(m, "router") for m in [
        attachments, contracts, customers, dashboard, documents, email_templates,
        euer, expenses, github, ical, invoices, leads, orders, pagespeed, search,
        time_entries, token_tracker,
    ])


def test_jwt_token_create_verify():
    from app.auth import create_access_token, verify_token
    token = create_access_token({"sub": "test-user"})
    payload = verify_token(token)
    assert payload["sub"] == "test-user"


def test_invoice_calculation():
    from decimal import Decimal
    from app.services.invoice_service import calculate_invoice_totals
    positions = [
        {"menge": "5.62", "einzelpreis": "95.00"},
        {"menge": "1", "einzelpreis": "150.19"},
    ]
    subtotal, tax, total = calculate_invoice_totals(
        positions, tax_rate=Decimal("19"), tax_exempt=False,
    )
    # 5.62 * 95 = 533.90; 1 * 150.19 = 150.19; sum = 684.09
    assert subtotal == Decimal("684.09")
    # 684.09 * 0.19 = 129.98 (rounded)
    assert tax == Decimal("129.98")
    assert total == Decimal("814.07")


def test_invoice_calculation_with_discount():
    from decimal import Decimal
    from app.services.invoice_service import calculate_invoice_totals
    positions = [{"menge": "1", "einzelpreis": "100"}]
    # 30% discount, tax-exempt
    subtotal, tax, total = calculate_invoice_totals(
        positions, tax_rate=Decimal("19"), tax_exempt=True,
        discount_type="percent", discount_value=30.0,
    )
    assert subtotal == Decimal("70.00")
    assert tax == Decimal("0.00")
    assert total == Decimal("70.00")


def test_invoice_calculation_discount_zero_ignored():
    """Regression: discount_value=0 must NOT crash and must result in no discount."""
    from decimal import Decimal
    from app.services.invoice_service import calculate_invoice_totals
    positions = [{"menge": "1", "einzelpreis": "100"}]
    subtotal, tax, total = calculate_invoice_totals(
        positions, tax_rate=Decimal("19"), tax_exempt=True,
        discount_type="percent", discount_value=0,
    )
    assert subtotal == Decimal("100.00")
    assert total == Decimal("100.00")


def test_safe_filename_strips_path():
    """Regression: attachment filenames must not contain path components."""
    from app.routers.attachments import _safe_filename
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("normal.pdf") == "normal.pdf"
    assert _safe_filename("") == "unnamed"


def test_period_pattern_matches_auto_positions():
    """Regression: refresh-drafts must detect auto-positions even after title rename."""
    import re
    pattern = re.compile(r"\(\d{4}-\d{2}-\d{2}\s+[–-]\s+\d{4}-\d{2}-\d{2}\)\s*$")
    assert pattern.search("Whatever (2026-03-01 – 2026-04-08)")
    assert pattern.search("Different Title (2026-01-01 – 2026-12-31)")
    assert not pattern.search("Manual position without dates")
