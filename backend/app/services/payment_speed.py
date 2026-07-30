"""Zahlungsgeschwindigkeit: Tage von Rechnungsdatum bis Bezahlt-Markierung.

Rein / ohne DB. Aggregation je Kunde; absteigend nach Ø-Tagen (langsamste zuerst).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean


def days_to_pay(invoice_date: date, paid_at: date | None) -> int | None:
    """Kalendertage zwischen Rechnungsdatum und Bezahlt-Datum.

    Negativ (Vorauszahlung / Datumstausch) wird auf 0 geklemmt — sonst würden
    Ausreißer den Kunden-Durchschnitt verfälschen.
    """
    if paid_at is None:
        return None
    return max(0, (paid_at - invoice_date).days)


@dataclass(frozen=True)
class PaymentSpeedRow:
    customer_id: str
    customer_name: str
    avg_days: float
    invoices_count: int
    min_days: int
    max_days: int


def aggregate_by_customer(
    rows: list[tuple[str, str, int]],
    *,
    limit: int | None = 20,
) -> list[PaymentSpeedRow]:
    """rows = (customer_id, customer_name, days). Sortiert Ø-Tage absteigend."""
    by_id: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for cid, name, days in rows:
        by_id[cid].append((name, days))

    out: list[PaymentSpeedRow] = []
    for cid, items in by_id.items():
        day_vals = [d for _, d in items]
        out.append(
            PaymentSpeedRow(
                customer_id=cid,
                customer_name=items[0][0],
                avg_days=round(mean(day_vals), 1),
                invoices_count=len(day_vals),
                min_days=min(day_vals),
                max_days=max(day_vals),
            )
        )

    out.sort(key=lambda r: (-r.avg_days, -r.invoices_count, r.customer_name.lower()))
    if limit is not None:
        return out[:limit]
    return out
