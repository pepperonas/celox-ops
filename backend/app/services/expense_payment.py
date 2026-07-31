"""Zahlungsstand einer Ausgabe synchron halten (rein/testbar)."""
from __future__ import annotations

from datetime import date


def normalize_payment(
    *,
    paid: bool,
    paid_at: date | None,
    expense_date: date | None,
) -> tuple[bool, date | None]:
    """Unbezahlt ⇒ kein paid_at. Bezahlt ⇒ paid_at oder Fallback auf Buchungsdatum."""
    if not paid:
        return False, None
    return True, paid_at or expense_date


def cash_date(
    *,
    paid: bool,
    paid_at: date | None,
    expense_date: date | None,
) -> date | None:
    """Datum für EÜR/Monatsaggregation — nur bei bezahlt; sonst None.

    Entspricht SQL ``coalesce(paid_at, date)`` unter ``paid IS TRUE``.
    """
    if not paid:
        return None
    return paid_at or expense_date


def counts_in_tax_year(
    *,
    paid: bool,
    paid_at: date | None,
    expense_date: date | None,
    year: int,
) -> bool:
    """True, wenn die Ausgabe im Steuerjahr ``year`` als Betriebsausgabe zählt."""
    d = cash_date(paid=paid, paid_at=paid_at, expense_date=expense_date)
    return d is not None and d.year == year
