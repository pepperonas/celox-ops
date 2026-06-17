"""Unit tests for invoice total calculation — pure logic, no DB required.
Run via: cd backend && pytest -v tests/test_invoice_service.py
"""
import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters-long")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

from app.services.invoice_service import calculate_invoice_totals  # noqa: E402

D = Decimal


def test_single_position_with_tax():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "100"}], tax_rate=D("19"), tax_exempt=False
    )
    assert (sub, tax, total) == (D("100.00"), D("19.00"), D("119.00"))


def test_decimal_quantity():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "2", "einzelpreis": "50.50"}], tax_rate=D("19"), tax_exempt=False
    )
    assert sub == D("101.00")
    assert tax == D("19.19")
    assert total == D("120.19")


def test_multiple_positions_sum_and_round():
    # 33.33 + 2*33.33 = 99.99; tax 19% = 18.9981 → 19.00
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "33.33"}, {"menge": "2", "einzelpreis": "33.33"}],
        tax_rate=D("19"), tax_exempt=False,
    )
    assert sub == D("99.99")
    assert tax == D("19.00")
    assert total == D("118.99")


def test_tax_exempt_has_zero_tax():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "100"}], tax_rate=D("19"), tax_exempt=True
    )
    assert (sub, tax, total) == (D("100.00"), D("0.00"), D("100.00"))


def test_percent_discount_with_tax():
    # 10% off 100 → 90; tax 19% → 17.10; total 107.10
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "100"}], tax_rate=D("19"), tax_exempt=False,
        discount_type="percent", discount_value=10.0,
    )
    assert sub == D("90.00")
    assert tax == D("17.10")
    assert total == D("107.10")


def test_fixed_discount_tax_exempt():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "100"}], tax_rate=D("19"), tax_exempt=True,
        discount_type="fixed", discount_value=25.0,
    )
    assert (sub, tax, total) == (D("75.00"), D("0.00"), D("75.00"))


def test_percent_discount_tax_exempt():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "200"}], tax_rate=D("19"), tax_exempt=True,
        discount_type="percent", discount_value=20.0,
    )
    assert sub == D("160.00")
    assert total == D("160.00")


def test_discount_zero_is_ignored():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "100"}], tax_rate=D("19"), tax_exempt=False,
        discount_type="percent", discount_value=0,
    )
    assert sub == D("100.00")
    assert total == D("119.00")


def test_discount_none_is_ignored():
    sub, _tax, total = calculate_invoice_totals(
        [{"menge": "1", "einzelpreis": "100"}], tax_rate=D("19"), tax_exempt=True,
        discount_type=None, discount_value=None,
    )
    assert sub == D("100.00")
    assert total == D("100.00")


def test_empty_positions():
    sub, tax, total = calculate_invoice_totals([], tax_rate=D("19"), tax_exempt=False)
    assert (sub, tax, total) == (D("0.00"), D("0.00"), D("0.00"))


def test_reduced_tax_rate():
    sub, tax, total = calculate_invoice_totals(
        [{"menge": "3", "einzelpreis": "10"}], tax_rate=D("7"), tax_exempt=False
    )
    assert sub == D("30.00")
    assert tax == D("2.10")
    assert total == D("32.10")


def test_fractional_quantity_rounds_subtotal():
    # 5.62 * 95 = 533.90
    sub, _tax, _total = calculate_invoice_totals(
        [{"menge": "5.62", "einzelpreis": "95.00"}], tax_rate=D("19"), tax_exempt=True
    )
    assert sub == D("533.90")
