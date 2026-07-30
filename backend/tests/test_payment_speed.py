"""Unit tests for payment-speed helpers (days + customer aggregation)."""
from datetime import date

from app.services.invoice_paid_at import sync_paid_at
from app.services.payment_speed import aggregate_by_customer, days_to_pay
from app.models.invoice import InvoiceStatus


def test_days_same_day_is_zero():
    assert days_to_pay(date(2026, 7, 1), date(2026, 7, 1)) == 0


def test_days_positive_span():
    assert days_to_pay(date(2026, 7, 1), date(2026, 7, 15)) == 14


def test_days_missing_paid_at():
    assert days_to_pay(date(2026, 7, 1), None) is None


def test_days_clamps_negative():
    # paid_at vor invoice_date (manuell/Backfill) → 0, kein negativer Durchschnitt
    assert days_to_pay(date(2026, 7, 10), date(2026, 7, 1)) == 0


def test_aggregate_sorts_fastest_first():
    rows = [
        ("a", "Alpha", 5),
        ("a", "Alpha", 15),  # Ø 10
        ("b", "Beta", 30),   # Ø 30
        ("c", "Gamma", 2),
        ("c", "Gamma", 4),   # Ø 3
    ]
    out = aggregate_by_customer(rows, limit=None)
    assert [r.customer_name for r in out] == ["Gamma", "Alpha", "Beta"]
    assert out[0].avg_days == 3.0
    assert out[0].invoices_count == 2
    assert out[1].avg_days == 10.0
    assert out[1].min_days == 5 and out[1].max_days == 15


def test_aggregate_respects_limit():
    rows = [(str(i), f"C{i}", i * 10) for i in range(5)]
    assert len(aggregate_by_customer(rows, limit=2)) == 2


class _Inv:
    def __init__(self, status, paid_at=None):
        self.status = status
        self.paid_at = paid_at


def test_sync_paid_at_sets_on_bezahlt():
    inv = _Inv(InvoiceStatus.bezahlt)
    sync_paid_at(inv, paid_on=date(2026, 7, 20))
    assert inv.paid_at == date(2026, 7, 20)


def test_sync_paid_at_keeps_existing():
    inv = _Inv(InvoiceStatus.bezahlt, paid_at=date(2026, 6, 1))
    sync_paid_at(inv, paid_on=date(2026, 7, 20))
    assert inv.paid_at == date(2026, 6, 1)


def test_sync_paid_at_clears_when_not_bezahlt():
    inv = _Inv(InvoiceStatus.gestellt, paid_at=date(2026, 6, 1))
    sync_paid_at(inv)
    assert inv.paid_at is None


def test_sync_paid_at_parses_iso_string():
    inv = _Inv(InvoiceStatus.bezahlt)
    sync_paid_at(inv, paid_on="2026-07-18")
    assert inv.paid_at == date(2026, 7, 18)
