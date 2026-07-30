"""Ausgaben-Turnus: Labels und Monats-/Jahresäquivalente. Rein / ohne DB."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.models.expense import ExpenseRecurrence

# Monate pro Periode (Jahr = 12; Woche = 12/52).
_MONTHS: dict[ExpenseRecurrence, Decimal] = {
    ExpenseRecurrence.weekly: Decimal("12") / Decimal("52"),
    ExpenseRecurrence.biweekly: Decimal("12") / Decimal("26"),
    ExpenseRecurrence.monthly: Decimal("1"),
    ExpenseRecurrence.quarterly: Decimal("3"),
    ExpenseRecurrence.semiannual: Decimal("6"),
    ExpenseRecurrence.yearly: Decimal("12"),
    ExpenseRecurrence.biennial: Decimal("24"),
    ExpenseRecurrence.quadrennial: Decimal("48"),
}

LABELS_DE: dict[ExpenseRecurrence, str] = {
    ExpenseRecurrence.weekly: "wöchentlich",
    ExpenseRecurrence.biweekly: "2 Wochen",
    ExpenseRecurrence.monthly: "monatlich",
    ExpenseRecurrence.quarterly: "quartalsweise",
    ExpenseRecurrence.semiannual: "halbjährlich",
    ExpenseRecurrence.yearly: "jährlich",
    ExpenseRecurrence.biennial: "2 Jahre",
    ExpenseRecurrence.quadrennial: "4 Jahre",
}


def coerce_recurrence(value) -> ExpenseRecurrence | None:
    if value is None or value == "":
        return None
    if isinstance(value, ExpenseRecurrence):
        return value
    return ExpenseRecurrence(str(value))


def label_de(value) -> str:
    """Deutsche Bezeichnung; einmalig → leerer String (Liste zeigt „—“)."""
    r = coerce_recurrence(value)
    if r is None:
        return ""
    return LABELS_DE[r]


def months_per_period(value) -> Decimal | None:
    r = coerce_recurrence(value)
    if r is None:
        return None
    return _MONTHS[r]


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def monthly_equivalent(amount: Decimal | float | int | str, recurrence) -> Decimal | None:
    """Betrag der Periode → Ø €/Monat."""
    months = months_per_period(recurrence)
    if months is None:
        return None
    return _money(Decimal(str(amount)) / months)


def yearly_equivalent(amount: Decimal | float | int | str, recurrence) -> Decimal | None:
    """Betrag der Periode → Ø €/Jahr."""
    monthly = monthly_equivalent(amount, recurrence)
    if monthly is None:
        return None
    return _money(monthly * Decimal("12"))


def normalize_recurrence_fields(
    *,
    recurrence=None,
    recurring: bool | None = None,
    recurrence_provided: bool = False,
    recurring_provided: bool = False,
) -> tuple[ExpenseRecurrence | None, bool]:
    """Create/Update: gesetztes recurrence schlägt; legacy recurring=true → monthly."""
    if recurrence_provided:
        r = coerce_recurrence(recurrence)
        return r, r is not None
    if recurring_provided:
        if recurring:
            return ExpenseRecurrence.monthly, True
        return None, False
    r = coerce_recurrence(recurrence)
    if r is not None:
        return r, True
    if recurring:
        return ExpenseRecurrence.monthly, True
    return None, False


def recurrence_from_billing_period(count: int | None, unit: str | None) -> ExpenseRecurrence:
    """Hostinger billing_period (+ unit) → Turnus. Fallback monatlich."""
    n = max(1, int(count or 1))
    u = (unit or "month").lower().rstrip("s")
    if u == "week":
        return ExpenseRecurrence.biweekly if n == 2 else ExpenseRecurrence.weekly
    if u == "month":
        if n == 3:
            return ExpenseRecurrence.quarterly
        if n == 6:
            return ExpenseRecurrence.semiannual
        if n == 12:
            return ExpenseRecurrence.yearly
        return ExpenseRecurrence.monthly
    if u == "year":
        if n == 2:
            return ExpenseRecurrence.biennial
        if n == 4:
            return ExpenseRecurrence.quadrennial
        return ExpenseRecurrence.yearly
    return ExpenseRecurrence.monthly
