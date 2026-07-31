"""Unit tests for expense recurrence helpers."""
from decimal import Decimal

import pytest

from app.models.expense import ExpenseRecurrence
from app.services.expense_recurrence import (
    coerce_recurrence,
    label_de,
    monthly_equivalent,
    months_per_period,
    normalize_recurrence_fields,
    recurrence_from_billing_period,
    yearly_equivalent,
)


def test_labels():
    assert label_de(None) == ""
    assert label_de("") == ""
    assert label_de(ExpenseRecurrence.monthly) == "monatlich"
    assert label_de("yearly") == "jährlich"
    for r in ExpenseRecurrence:
        assert label_de(r)


def test_coerce_recurrence():
    assert coerce_recurrence(None) is None
    assert coerce_recurrence("") is None
    assert coerce_recurrence(ExpenseRecurrence.weekly) is ExpenseRecurrence.weekly
    assert coerce_recurrence("monthly") is ExpenseRecurrence.monthly


def test_months_per_period_all_values():
    assert months_per_period(None) is None
    assert months_per_period(ExpenseRecurrence.monthly) == Decimal("1")
    assert months_per_period(ExpenseRecurrence.yearly) == Decimal("12")
    assert months_per_period(ExpenseRecurrence.quadrennial) == Decimal("48")


def test_monthly_equivalent_monthly_is_same():
    assert monthly_equivalent(Decimal("11.99"), ExpenseRecurrence.monthly) == Decimal("11.99")


def test_monthly_equivalent_yearly():
    assert monthly_equivalent(Decimal("120"), ExpenseRecurrence.yearly) == Decimal("10.00")


@pytest.mark.parametrize(
    "amount,rec",
    [
        (Decimal("52"), ExpenseRecurrence.weekly),
        (Decimal("30"), ExpenseRecurrence.quarterly),
        (Decimal("60"), ExpenseRecurrence.semiannual),
        (Decimal("24"), ExpenseRecurrence.biennial),
        (Decimal("48"), ExpenseRecurrence.quadrennial),
        (Decimal("26"), ExpenseRecurrence.biweekly),
    ],
)
def test_monthly_equivalent_matrix(amount, rec):
    months = months_per_period(rec)
    assert monthly_equivalent(amount, rec) == (amount / months).quantize(Decimal("0.01"))


def test_yearly_equivalent_monthly():
    assert yearly_equivalent(Decimal("10"), ExpenseRecurrence.monthly) == Decimal("120.00")


def test_yearly_equivalent_quadrennial():
    # 48 € alle 4 Jahre → 1 €/Monat → 12 €/Jahr
    assert yearly_equivalent(Decimal("48"), ExpenseRecurrence.quadrennial) == Decimal("12.00")


def test_yearly_follows_monthly_rounding():
    m = monthly_equivalent(Decimal("10"), ExpenseRecurrence.weekly)
    assert yearly_equivalent(Decimal("10"), ExpenseRecurrence.weekly) == (
        m * Decimal("12")
    ).quantize(Decimal("0.01"))


def test_none_recurrence_no_equivalent():
    assert monthly_equivalent(10, None) is None
    assert yearly_equivalent(10, None) is None


def test_normalize_recurrence_explicit():
    r, flag = normalize_recurrence_fields(
        recurrence=ExpenseRecurrence.weekly, recurrence_provided=True,
    )
    assert r == ExpenseRecurrence.weekly and flag is True
    r, flag = normalize_recurrence_fields(recurrence=None, recurrence_provided=True)
    assert r is None and flag is False


def test_normalize_legacy_recurring_true():
    r, flag = normalize_recurrence_fields(recurring=True, recurring_provided=True)
    assert r == ExpenseRecurrence.monthly and flag is True


def test_normalize_legacy_recurring_false():
    r, flag = normalize_recurrence_fields(recurring=False, recurring_provided=True)
    assert r is None and flag is False


def test_normalize_recurrence_beats_legacy_when_both_present_via_recurrence_provided():
    r, flag = normalize_recurrence_fields(
        recurrence=ExpenseRecurrence.yearly,
        recurring=False,
        recurrence_provided=True,
        recurring_provided=True,
    )
    assert r == ExpenseRecurrence.yearly and flag is True


def test_normalize_fallback_without_flags():
    r, flag = normalize_recurrence_fields(recurrence=ExpenseRecurrence.quarterly)
    assert r == ExpenseRecurrence.quarterly and flag is True
    r, flag = normalize_recurrence_fields(recurring=True)
    assert r == ExpenseRecurrence.monthly and flag is True
    r, flag = normalize_recurrence_fields()
    assert r is None and flag is False


@pytest.mark.parametrize(
    "count,unit,expected",
    [
        (1, "month", ExpenseRecurrence.monthly),
        (1, "months", ExpenseRecurrence.monthly),
        (3, "month", ExpenseRecurrence.quarterly),
        (6, "months", ExpenseRecurrence.semiannual),
        (12, "month", ExpenseRecurrence.yearly),
        (1, "year", ExpenseRecurrence.yearly),
        (1, "years", ExpenseRecurrence.yearly),
        (2, "years", ExpenseRecurrence.biennial),
        (4, "year", ExpenseRecurrence.quadrennial),
        (1, "week", ExpenseRecurrence.weekly),
        (2, "week", ExpenseRecurrence.biweekly),
        (2, "weeks", ExpenseRecurrence.biweekly),
        (None, None, ExpenseRecurrence.monthly),
        (1, "day", ExpenseRecurrence.monthly),
        (0, "month", ExpenseRecurrence.monthly),
    ],
)
def test_hostinger_billing_mapping_matrix(count, unit, expected):
    assert recurrence_from_billing_period(count, unit) == expected


def test_hostinger_billing_mapping_smoke():
    assert recurrence_from_billing_period(1, "month") == ExpenseRecurrence.monthly
    assert recurrence_from_billing_period(1, "year") == ExpenseRecurrence.yearly
    assert recurrence_from_billing_period(2, "years") == ExpenseRecurrence.biennial
    assert recurrence_from_billing_period(4, "year") == ExpenseRecurrence.quadrennial
    assert recurrence_from_billing_period(3, "month") == ExpenseRecurrence.quarterly
    assert recurrence_from_billing_period(6, "months") == ExpenseRecurrence.semiannual
    assert recurrence_from_billing_period(1, "week") == ExpenseRecurrence.weekly
    assert recurrence_from_billing_period(2, "week") == ExpenseRecurrence.biweekly
