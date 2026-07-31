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
