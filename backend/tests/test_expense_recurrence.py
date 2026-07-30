"""Unit tests for expense recurrence helpers."""
from decimal import Decimal

from app.models.expense import ExpenseRecurrence
from app.services.expense_recurrence import (
    label_de,
    monthly_equivalent,
    normalize_recurrence_fields,
    recurrence_from_billing_period,
    yearly_equivalent,
)


def test_labels():
    assert label_de(None) == ""
    assert label_de(ExpenseRecurrence.monthly) == "monatlich"
    assert label_de("yearly") == "jährlich"


def test_monthly_equivalent_monthly_is_same():
    assert monthly_equivalent(Decimal("11.99"), ExpenseRecurrence.monthly) == Decimal("11.99")


def test_monthly_equivalent_yearly():
    assert monthly_equivalent(Decimal("120"), ExpenseRecurrence.yearly) == Decimal("10.00")


def test_yearly_equivalent_monthly():
    assert yearly_equivalent(Decimal("10"), ExpenseRecurrence.monthly) == Decimal("120.00")


def test_yearly_equivalent_quadrennial():
    # 48 € alle 4 Jahre → 1 €/Monat → 12 €/Jahr
    assert yearly_equivalent(Decimal("48"), ExpenseRecurrence.quadrennial) == Decimal("12.00")


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


def test_hostinger_billing_mapping():
    assert recurrence_from_billing_period(1, "month") == ExpenseRecurrence.monthly
    assert recurrence_from_billing_period(1, "year") == ExpenseRecurrence.yearly
    assert recurrence_from_billing_period(2, "years") == ExpenseRecurrence.biennial
    assert recurrence_from_billing_period(4, "year") == ExpenseRecurrence.quadrennial
    assert recurrence_from_billing_period(3, "month") == ExpenseRecurrence.quarterly
    assert recurrence_from_billing_period(6, "months") == ExpenseRecurrence.semiannual
    assert recurrence_from_billing_period(1, "week") == ExpenseRecurrence.weekly
    assert recurrence_from_billing_period(2, "week") == ExpenseRecurrence.biweekly
