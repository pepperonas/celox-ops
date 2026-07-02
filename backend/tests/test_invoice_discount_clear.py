"""Regression test for the discount-clear bug (bug hunt 2026-07):
removing a discount on PUT /invoices/{id} must recompute totals WITHOUT the old
discount. Pure calc-level test (no DB) — mirrors the branch in update_invoice.
"""
from decimal import Decimal

from app.services.invoice_service import calculate_invoice_totals

POSITIONS = [
    {"position": 1, "beschreibung": "Arbeit", "menge": Decimal("10"),
     "einheit": "Stunden", "einzelpreis": Decimal("100"), "gesamt": Decimal("1000")},
]


def test_totals_with_10_percent_discount():
    subtotal, tax, total = calculate_invoice_totals(
        POSITIONS, Decimal("19.00"), False, discount_type="percent", discount_value=10.0
    )
    # 1000 net − 10 % = 900 → +19 % = 1071.00
    assert subtotal == Decimal("900.00")
    assert total == Decimal("1071.00")


def test_clearing_discount_recomputes_full_total():
    # This is the exact scenario the frontend triggers: discount toggled off →
    # discount_type/value arrive as None → totals must be the undiscounted ones.
    subtotal, tax, total = calculate_invoice_totals(
        POSITIONS, Decimal("19.00"), False, discount_type=None, discount_value=None
    )
    assert subtotal == Decimal("1000.00")
    assert total == Decimal("1190.00")


def test_zero_discount_value_is_ignored():
    # Guard: discount_value 0 must not change the total (documented invariant).
    _s, _t, total = calculate_invoice_totals(
        POSITIONS, Decimal("19.00"), False, discount_type="percent", discount_value=0.0
    )
    assert total == Decimal("1190.00")
