from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract, ContractStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.order import Order, OrderStatus

router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


class TaskItem(BaseModel):
    type: str
    priority: str
    title: str
    subtitle: str
    detail: str
    link: str
    date: str


class TasksResponse(BaseModel):
    tasks: list[TaskItem]
    count: int


@router.get("", response_model=TasksResponse)
async def get_tasks(
    db: AsyncSession = Depends(get_db),
) -> TasksResponse:
    today = date.today()
    in_30_days = today + timedelta(days=30)
    in_60_days = today + timedelta(days=60)

    tasks: list[TaskItem] = []

    # 1. Overdue invoices (status=gestellt, due_date < today)
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(
            Invoice.status == InvoiceStatus.gestellt,
            Invoice.due_date < today,
        )
    )
    for inv in result.scalars().unique():
        customer_name = inv.customer.name if inv.customer else "Unbekannt"
        tasks.append(
            TaskItem(
                type="overdue_invoice",
                priority="critical",
                title=f"Rechnung {inv.invoice_number} überfällig",
                subtitle=customer_name,
                detail=f"{inv.title} — fällig seit {inv.due_date.isoformat()}",
                link=f"/rechnungen/{inv.id}",
                date=inv.due_date.isoformat(),
            )
        )

    # 2. Invoices due within 30 days (status=gestellt, due_date >= today and <= today+30)
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(
            Invoice.status == InvoiceStatus.gestellt,
            Invoice.due_date >= today,
            Invoice.due_date <= in_30_days,
        )
    )
    for inv in result.scalars().unique():
        customer_name = inv.customer.name if inv.customer else "Unbekannt"
        tasks.append(
            TaskItem(
                type="due_invoice",
                priority="warning",
                title=f"Rechnung {inv.invoice_number} fällig",
                subtitle=customer_name,
                detail=f"{inv.title} — fällig am {inv.due_date.isoformat()}",
                link=f"/rechnungen/{inv.id}",
                date=inv.due_date.isoformat(),
            )
        )

    # 3. Draft invoices not yet sent
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.status == InvoiceStatus.entwurf)
    )
    for inv in result.scalars().unique():
        customer_name = inv.customer.name if inv.customer else "Unbekannt"
        tasks.append(
            TaskItem(
                type="draft_invoice",
                priority="info",
                title=f"Entwurf: {inv.invoice_number}",
                subtitle=customer_name,
                detail=f"{inv.title} — noch nicht versendet",
                link=f"/rechnungen/{inv.id}",
                date=inv.created_at.date().isoformat()
                if inv.created_at
                else today.isoformat(),
            )
        )

    # 4. Contracts expiring within 60 days
    result = await db.execute(
        select(Contract)
        .options(joinedload(Contract.customer))
        .where(
            Contract.status == ContractStatus.aktiv,
            Contract.end_date.isnot(None),
            Contract.end_date <= in_60_days,
            Contract.end_date >= today,
        )
    )
    for c in result.scalars().unique():
        customer_name = c.customer.name if c.customer else "Unbekannt"
        tasks.append(
            TaskItem(
                type="expiring_contract",
                priority="warning",
                title=f"Vertrag läuft aus: {c.title}",
                subtitle=customer_name,
                detail=f"Endet am {c.end_date.isoformat()}"
                if c.end_date
                else "",
                link=f"/vertraege/{c.id}",
                date=c.end_date.isoformat() if c.end_date else today.isoformat(),
            )
        )

    # 5. Active orders (in_arbeit)
    result = await db.execute(
        select(Order)
        .options(joinedload(Order.customer))
        .where(Order.status == OrderStatus.in_arbeit)
    )
    for o in result.scalars().unique():
        customer_name = o.customer.name if o.customer else "Unbekannt"
        tasks.append(
            TaskItem(
                type="active_order",
                priority="info",
                title=f"Auftrag: {o.title}",
                subtitle=customer_name,
                detail="In Arbeit",
                link=f"/auftraege/{o.id}",
                date=o.start_date.isoformat()
                if o.start_date
                else o.created_at.date().isoformat()
                if o.created_at
                else today.isoformat(),
            )
        )

    # Sort: critical first, then warning, then info
    priority_order = {"critical": 0, "warning": 1, "info": 2}
    tasks.sort(key=lambda t: (priority_order.get(t.priority, 9), t.date))

    return TasksResponse(tasks=tasks, count=len(tasks))
