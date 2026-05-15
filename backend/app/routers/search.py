"""Global search across customers, invoices, orders, contracts, leads."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.order import Order

router = APIRouter(
    prefix="/api/search",
    tags=["search"],
    dependencies=[Depends(get_current_user)],
)


class SearchHit(BaseModel):
    id: str
    type: str  # "customer" | "invoice" | "order" | "contract" | "lead"
    title: str
    subtitle: str | None = None
    url: str  # Frontend route to navigate to


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
    total: int


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=2, max_length=100),
    limit_per_type: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search across all major entities. Case-insensitive substring matching."""
    pattern = f"%{q.strip()}%"
    hits: list[SearchHit] = []

    # Customers — name, company, email
    res = await db.execute(
        select(Customer)
        .where(
            or_(
                Customer.name.ilike(pattern),
                Customer.company.ilike(pattern),
                Customer.email.ilike(pattern),
            )
        )
        .limit(limit_per_type)
    )
    for c in res.scalars().all():
        hits.append(SearchHit(
            id=str(c.id),
            type="customer",
            title=c.name,
            subtitle=c.company or c.email or None,
            url=f"/kunden/{c.id}",
        ))

    # Invoices — invoice_number, title
    res = await db.execute(
        select(Invoice)
        .where(
            or_(
                Invoice.invoice_number.ilike(pattern),
                Invoice.title.ilike(pattern),
            )
        )
        .order_by(Invoice.invoice_date.desc())
        .limit(limit_per_type)
    )
    for inv in res.scalars().all():
        hits.append(SearchHit(
            id=str(inv.id),
            type="invoice",
            title=f"{inv.invoice_number} — {inv.title}",
            subtitle=f"{float(inv.total):.2f} € · {inv.status.value}",
            url=f"/rechnungen/{inv.id}",
        ))

    # Orders — title
    res = await db.execute(
        select(Order)
        .where(Order.title.ilike(pattern))
        .order_by(Order.start_date.desc().nulls_last())
        .limit(limit_per_type)
    )
    for o in res.scalars().all():
        hits.append(SearchHit(
            id=str(o.id),
            type="order",
            title=o.title,
            subtitle=f"Auftrag · {o.status.value}",
            url=f"/auftraege/{o.id}",
        ))

    # Contracts — title
    res = await db.execute(
        select(Contract)
        .where(Contract.title.ilike(pattern))
        .limit(limit_per_type)
    )
    for con in res.scalars().all():
        hits.append(SearchHit(
            id=str(con.id),
            type="contract",
            title=con.title,
            subtitle=f"Vertrag · {con.type.value}",
            url=f"/vertraege/{con.id}",
        ))

    # Leads — name, url, company (all may be NULL — ilike on NULL safely returns NULL)
    res = await db.execute(
        select(Lead)
        .where(
            or_(
                Lead.name.ilike(pattern),
                Lead.company.ilike(pattern),
                Lead.url.ilike(pattern),
            )
        )
        .limit(limit_per_type)
    )
    for lead in res.scalars().all():
        hits.append(SearchHit(
            id=str(lead.id),
            type="lead",
            title=lead.name or lead.url,
            subtitle=lead.company or "Lead",
            url="/vorgemerkt",
        ))

    return SearchResponse(query=q, hits=hits, total=len(hits))
