"""paid_at am Invoice setzen/löschen, wenn der Status auf/von bezahlt wechselt.

Systemfeld — nicht über InvoiceUpdate/GoBD-Riegel. Rein bis auf den
Geschäftstag-Fallback (injizierbar).
"""
from __future__ import annotations

from datetime import date, datetime

from app.models.invoice import InvoiceStatus
from app.services.business_time import today as business_today


def _as_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    # ISO oder DD.MM.YYYY (Kontoauszug-Vorschläge)
    if "." in text and text.count(".") == 2:
        d, m, y = text.split(".")
        return date(int(y), int(m), int(d))
    return date.fromisoformat(text[:10])


def sync_paid_at(invoice, *, paid_on: date | datetime | str | None = None) -> None:
    """Status → bezahlt: paid_at setzen (einmalig). Sonst: löschen.

    `paid_on` = Buchungsdatum (Kontoauszug); sonst Geschäftstag. Ein bereits
    gesetztes paid_at bleibt stehen (Teilzahlungen / erneutes Speichern).
    """
    status = getattr(invoice.status, "value", invoice.status)
    if status == InvoiceStatus.bezahlt.value:
        if invoice.paid_at is None:
            invoice.paid_at = _as_date(paid_on) or business_today()
    else:
        invoice.paid_at = None
