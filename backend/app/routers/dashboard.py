from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract, ContractStatus
from app.models.invoice import Invoice, InvoiceStatus

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


class DashboardStats(BaseModel):
    revenue_month: Decimal
    revenue_year: Decimal
    open_invoices_count: int
    open_invoices_sum: Decimal
    overdue_invoices_count: int
    overdue_invoices_sum: Decimal
    active_contracts_count: int
    active_contracts_monthly_sum: Decimal


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    today = date.today()

    # Revenue this month (paid invoices)
    result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.bezahlt,
            func.extract("year", Invoice.invoice_date) == current_year,
            func.extract("month", Invoice.invoice_date) == current_month,
        )
    )
    revenue_month = result.scalar_one()

    # Revenue this year
    result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.bezahlt,
            func.extract("year", Invoice.invoice_date) == current_year,
        )
    )
    revenue_year = result.scalar_one()

    # Open invoices (gestellt)
    result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.gestellt,
        )
    )
    row = result.one()
    open_invoices_count = row[0]
    open_invoices_sum = row[1]

    # Overdue invoices
    result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status.in_([InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig]),
            Invoice.due_date < today,
        )
    )
    row = result.one()
    overdue_invoices_count = row[0]
    overdue_invoices_sum = row[1]

    # Active contracts
    result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Contract.monthly_amount), 0),
        ).where(Contract.status == ContractStatus.aktiv)
    )
    row = result.one()
    active_contracts_count = row[0]
    active_contracts_monthly_sum = row[1]

    return DashboardStats(
        revenue_month=revenue_month,
        revenue_year=revenue_year,
        open_invoices_count=open_invoices_count,
        open_invoices_sum=open_invoices_sum,
        overdue_invoices_count=overdue_invoices_count,
        overdue_invoices_sum=overdue_invoices_sum,
        active_contracts_count=active_contracts_count,
        active_contracts_monthly_sum=active_contracts_monthly_sum,
    )
