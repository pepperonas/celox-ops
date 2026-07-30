"""Zahlungsgeschwindigkeit: Tage von Rechnungsdatum bis Bezahlt-Markierung.

Rein / ohne DB. Aggregation je Kunde; schnelle Zahler oben, Kunden mit
überfälligen offenen Rechnungen immer ans Ende (rot im UI).
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


def open_days(invoice_date: date, today: date) -> int:
    """Wie lange eine noch offene Rechnung schon steht (heute − Rechnungsdatum)."""
    return max(0, (today - invoice_date).days)


@dataclass(frozen=True)
class PaymentSpeedRow:
    customer_id: str
    customer_name: str
    avg_days: float
    invoices_count: int
    min_days: int
    max_days: int
    has_overdue: bool = False
    overdue_count: int = 0


def aggregate_by_customer(
    paid_rows: list[tuple[str, str, int]],
    *,
    overdue_rows: list[tuple[str, str, int]] | None = None,
    limit: int | None = 20,
) -> list[PaymentSpeedRow]:
    """paid_rows / overdue_rows = (customer_id, customer_name, days).

    Sortierung: ohne Überfälligkeit nach Ø-Tagen aufsteigend; Kunden mit
    mind. einer überfälligen Rechnung immer ans Ende (dort nach Anzeigewert
    absteigend = schlimmste ganz unten). Anzeigewert bei Überfälligkeit =
    max(Ø bezahlt, längste offene Überfälligkeit), damit der Balken die
    aktuelle Lage zeigt.
    """
    overdue_rows = overdue_rows or []

    paid_by: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for cid, name, days in paid_rows:
        paid_by[cid].append((name, days))

    overdue_by: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for cid, name, days in overdue_rows:
        overdue_by[cid].append((name, days))

    all_ids = set(paid_by) | set(overdue_by)
    out: list[PaymentSpeedRow] = []
    for cid in all_ids:
        paid = paid_by.get(cid, [])
        overdue = overdue_by.get(cid, [])
        name = (paid or overdue)[0][0]
        paid_days = [d for _, d in paid]
        overdue_days = [d for _, d in overdue]
        has_overdue = bool(overdue)

        if has_overdue:
            paid_avg = mean(paid_days) if paid_days else 0.0
            worst_open = max(overdue_days)
            display = round(max(paid_avg, worst_open), 1)
            all_vals = paid_days + overdue_days
        else:
            display = round(mean(paid_days), 1)
            all_vals = paid_days

        out.append(
            PaymentSpeedRow(
                customer_id=cid,
                customer_name=name,
                avg_days=display,
                invoices_count=len(all_vals),
                min_days=min(all_vals),
                max_days=max(all_vals),
                has_overdue=has_overdue,
                overdue_count=len(overdue),
            )
        )

    # Überfällige zuletzt; unter den Sauberen schnell→langsam; unter den
    # Überfälligen schlimmste ganz unten.
    out.sort(
        key=lambda r: (
            r.has_overdue,
            -r.avg_days if r.has_overdue else r.avg_days,
            -r.invoices_count,
            r.customer_name.lower(),
        )
    )
    if limit is not None:
        # Limit gilt für die „normalen“; Überfällige bleiben immer sichtbar.
        clean = [r for r in out if not r.has_overdue][:limit]
        overdue = [r for r in out if r.has_overdue]
        return clean + overdue
    return out
