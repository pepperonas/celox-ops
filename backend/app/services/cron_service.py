from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus


async def check_overdue_invoices(db: AsyncSession) -> int:
    """Gestellte Rechnungen nach Fälligkeitsdatum als überfällig markieren.

    Returns the number of invoices marked as overdue.
    """
    today = date.today()
    result = await db.execute(
        select(Invoice).where(
            Invoice.status == InvoiceStatus.gestellt,
            Invoice.due_date < today,
        )
    )
    count = 0
    for inv in result.scalars().all():
        inv.status = InvoiceStatus.ueberfaellig
        count += 1
    return count
