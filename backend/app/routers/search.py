"""Globale Suche über Kunden, Rechnungen, Aufträge, Verträge und Pipeline-Leads."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.rainmaker_lead import RainmakerLead

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


# Status-Kurzlabels für den Untertitel (die Enum-Werte sind englisch/technisch).
_LEAD_STATUS_LABELS = {
    "new": "Neu", "contacted": "Kontaktiert", "connected": "Vernetzt",
    "in_conversation": "Im Gespräch", "proposal": "Angebot",
    "won": "Gewonnen", "lost": "Verloren", "dormant": "Ruhend",
}


def lead_hit(lead) -> SearchHit:
    """Pipeline-Lead → Suchtreffer (rein, damit Titel/Untertitel/URL testbar sind).
    Untertitel nennt das Wichtigste zur Unterscheidung gleichnamiger Firmen:
    Ansprechpartner bzw. Target, dazu der Pipeline-Status."""
    status = getattr(lead.status, "value", str(lead.status))
    parts = [p for p in (lead.contact_name, lead.target) if p]
    parts.append(_LEAD_STATUS_LABELS.get(status, status))
    return SearchHit(
        id=str(lead.id),
        type="lead",
        title=lead.company,
        subtitle=" · ".join(parts),
        url=f"/pipeline/leads/{lead.id}",
    )


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

    # Pipeline-Leads (rainmaker_leads). NICHT das alte `Lead`-Modell der
    # entfernten „Vorgemerkt"-Merkliste — das ist leer und verlinkte auf eine
    # tote Route. Felder inkl. Entscheider + Target, damit man auch eine
    # Kampagne („bcs") oder die Geschäftsführung findet.
    res = await db.execute(
        select(RainmakerLead)
        .where(
            or_(
                RainmakerLead.company.ilike(pattern),
                RainmakerLead.contact_name.ilike(pattern),
                RainmakerLead.email.ilike(pattern),
                RainmakerLead.website.ilike(pattern),
                RainmakerLead.decision_maker.ilike(pattern),
                RainmakerLead.target.ilike(pattern),
            )
        )
        .order_by(RainmakerLead.updated_at.desc())
        .limit(limit_per_type)
    )
    for lead in res.scalars().all():
        hits.append(lead_hit(lead))

    return SearchResponse(query=q, hits=hits, total=len(hits))
