import json
import math
import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.activity import Activity
from app.models.attachment import Attachment
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.time_entry import TimeEntry
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetail,
    CustomerResponse,
    CustomerUpdate,
    TodoSuggestionResponse,
)
from app.services.filenames import customer_label, download_name
from app.services.business_time import now as business_now, today as business_today

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_customers(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Customer)
    count_query = select(func.count()).select_from(Customer)

    if search:
        search_filter = f"%{search}%"
        condition = (
            Customer.name.ilike(search_filter)
            | Customer.email.ilike(search_filter)
            | Customer.company.ilike(search_filter)
            | Customer.website.ilike(search_filter)
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Customer, sort_by, Customer.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    customers = result.scalars().all()

    return {
        "items": [CustomerResponse.model_validate(c) for c in customers],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CustomerDetail:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    orders_count = await db.execute(
        select(func.count()).where(Order.customer_id == customer_id)
    )
    contracts_count = await db.execute(
        select(func.count()).where(Contract.customer_id == customer_id)
    )
    invoices_count = await db.execute(
        select(func.count()).where(Invoice.customer_id == customer_id)
    )

    detail = CustomerDetail.model_validate(customer)
    detail.orders_count = orders_count.scalar_one()
    detail.contracts_count = contracts_count.scalar_one()
    detail.invoices_count = invoices_count.scalar_one()
    return detail


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    customer = Customer(**data.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)

    await db.flush()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    # Check references
    orders_count = await db.execute(
        select(func.count()).where(Order.customer_id == customer_id)
    )
    if orders_count.scalar_one() > 0:
        raise HTTPException(
            status_code=400,
            detail="Kunde hat zugehörige Aufträge und kann nicht gelöscht werden",
        )

    contracts_count = await db.execute(
        select(func.count()).where(Contract.customer_id == customer_id)
    )
    if contracts_count.scalar_one() > 0:
        raise HTTPException(
            status_code=400,
            detail="Kunde hat zugehörige Verträge und kann nicht gelöscht werden",
        )

    invoices_count = await db.execute(
        select(func.count()).where(Invoice.customer_id == customer_id)
    )
    if invoices_count.scalar_one() > 0:
        raise HTTPException(
            status_code=400,
            detail="Kunde hat zugehörige Rechnungen und kann nicht gelöscht werden",
        )

    await db.delete(customer)


def _dsgvo_serialize(obj):
    """JSON serializer for DSGVO export."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "value") and isinstance(obj.value, str):
        return obj.value
    if hasattr(obj, "hex"):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def _row_to_dict(row) -> dict:
    d = {}
    for col in row.__table__.columns:
        d[col.name] = getattr(row, col.name)
    return d


@router.get("/{customer_id}/dsgvo-export")
async def dsgvo_export(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """DSGVO Art. 15 — Auskunftsrecht: Alle Daten eines Kunden als JSON."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    # Orders
    orders_result = await db.execute(
        select(Order).where(Order.customer_id == customer_id)
    )
    orders = [_row_to_dict(o) for o in orders_result.scalars().all()]

    # Contracts
    contracts_result = await db.execute(
        select(Contract).where(Contract.customer_id == customer_id)
    )
    contracts = [_row_to_dict(c) for c in contracts_result.scalars().all()]

    # Invoices
    invoices_result = await db.execute(
        select(Invoice).where(Invoice.customer_id == customer_id)
    )
    invoices = [_row_to_dict(i) for i in invoices_result.scalars().all()]

    # Time entries
    time_entries_result = await db.execute(
        select(TimeEntry).where(TimeEntry.customer_id == customer_id)
    )
    time_entries = [_row_to_dict(t) for t in time_entries_result.scalars().all()]

    # Activities
    activities_result = await db.execute(
        select(Activity).where(Activity.customer_id == customer_id)
    )
    activities = [_row_to_dict(a) for a in activities_result.scalars().all()]

    # Attachments (filenames only)
    attachments_result = await db.execute(
        select(Attachment).where(Attachment.customer_id == customer_id)
    )
    attachments = [
        {
            "id": str(a.id),
            "original_name": a.original_name,
            "content_type": a.content_type,
            "size": a.size,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in attachments_result.scalars().all()
    ]

    export = {
        "export_type": "DSGVO Art. 15 — Auskunft",
        "export_date": business_now().isoformat(),
        "kunde": _row_to_dict(customer),
        "auftraege": orders,
        "vertraege": contracts,
        "rechnungen": invoices,
        "zeiterfassung": time_entries,
        "aktivitaeten": activities,
        "anhaenge": attachments,
    }

    json_str = json.dumps(export, default=_dsgvo_serialize, ensure_ascii=False, indent=2)

    filename = download_name(
        "DSGVO-Export", customer_label(customer), business_today().isoformat(), ext="json"
    )
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------- #
#  KI-Vorschläge für To-dos zu diesem Kunden
# --------------------------------------------------------------------------- #
@router.post("/{customer_id}/todo-suggestions", response_model=TodoSuggestionResponse)
async def suggest_customer_todos(
    customer_id: uuid.UUID,
    force: bool = Query(False, description="Cache umgehen und neu ableiten"),
    hint: str = Query("", max_length=2000, description="Eigener Hinweis an die KI"),
    db: AsyncSession = Depends(get_db),
) -> TodoSuggestionResponse:
    """Leitet aus den vorliegenden Kundendaten Aufgaben ab. **Legt nichts an.**

    Die fünf regelbasierten Hinweise (`routers/tasks.py`) gehen als „bereits
    erkannt" in den Kontext, damit die KI sie nicht wiederholt — der Mehrwert
    liegt in Notizen, Kontakthistorie und Lead-Vorgeschichte.

    Kosten: ein Aufruf liegt im Cent-Bereich; ein unveränderter Kunde liefert den
    Vorschlag aus dem Cache **ohne** KI-Aufruf (auch bei erreichtem Budget).
    """
    from app.models.ai_lead_run import AiLeadRun
    from app.models.compliance_record import ComplianceRecord
    from app.models.customer_todo_suggestion import CustomerTodoSuggestion
    from app.models.document_template import DocumentTemplate
    from app.models.lead_website_analysis import LeadWebsiteAnalysis
    from app.models.rainmaker_lead import RainmakerLead
    from app.models.todo import Todo, TodoStatus
    from app.schemas.customer import TodoSuggestion
    from app.schemas.rainmaker import AiRunCost
    from app.services import ai_budget, customer_todo_ai
    from app.services.ai_key import require_anthropic_key
    from app.services.ai_pricing import Usage, get_pricing
    from app.services.exchange_service import get_usd_eur_rate

    customer = (await db.execute(
        select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    # Alle Quellen einsammeln (owner-scoped über die Tenancy-Events).
    orders = (await db.execute(
        select(Order).where(Order.customer_id == customer_id))).scalars().all()
    contracts = (await db.execute(
        select(Contract).where(Contract.customer_id == customer_id))).scalars().all()
    invoices = (await db.execute(
        select(Invoice).where(Invoice.customer_id == customer_id)
        .order_by(Invoice.invoice_date.desc()).limit(40))).scalars().all()
    activities = (await db.execute(
        select(Activity).where(Activity.customer_id == customer_id)
        .order_by(Activity.created_at.desc()).limit(30))).scalars().all()
    attachments = (await db.execute(
        select(Attachment).where(Attachment.customer_id == customer_id)
        .limit(40))).scalars().all()
    open_todos = (await db.execute(
        select(Todo).where(Todo.customer_id == customer_id,
                           Todo.status == TodoStatus.offen))).scalars().all()

    # Pflicht-Rechtsdokumente ohne Unterschrift.
    required = (await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.compliance_required.is_(True)))).scalars().all()
    signed = {r.template_id for r in (await db.execute(
        select(ComplianceRecord).where(
            ComplianceRecord.customer_id == customer_id,
            ComplianceRecord.signed_at.isnot(None)))).scalars().all()}
    compliance_missing = [t.name for t in required if t.id not in signed]

    # Falls dieser Kunde aus einem Lead entstanden ist: Lead + neueste Analyse.
    lead = (await db.execute(
        select(RainmakerLead).where(
            RainmakerLead.customer_id == customer_id))).scalars().first()
    lead_analysis = None
    if lead is not None:
        row = (await db.execute(
            select(LeadWebsiteAnalysis).where(LeadWebsiteAnalysis.lead_id == lead.id)
            .order_by(LeadWebsiteAnalysis.created_at.desc()).limit(1))).scalars().first()
        if row is not None:
            lead_analysis = {
                "overall_score": row.overall_score,
                "rating": row.rating,
                "findings": json.loads(row.findings) if row.findings else [],
            }

    today = business_today()
    context = customer_todo_ai.build_context(
        customer=customer, orders=orders, contracts=contracts, invoices=invoices,
        activities=activities, attachments=attachments, todos=open_todos,
        compliance_missing=compliance_missing, lead=lead,
        lead_analysis=lead_analysis, today=today)

    model, budget_eur, spent = await ai_budget.ai_context(db)
    wanted = customer_todo_ai.context_hash(context + hint, model)

    cache = (await db.execute(
        select(CustomerTodoSuggestion).where(
            CustomerTodoSuggestion.customer_id == customer_id))).scalar_one_or_none()
    if not force and cache and cache.context_hash == wanted:
        stored = json.loads(cache.payload)
        zero = Usage()
        return TodoSuggestionResponse(
            suggestions=[TodoSuggestion(**s) for s in stored.get("suggestions", [])],
            ignored=stored.get("ignored", []), cached=True,
            run=AiRunCost(model=model, cost_usd=0.0, cost_eur=0.0, **zero.as_dict()),
            budget=ai_budget.budget_status(spent, budget_eur))

    api_key = await require_anthropic_key(db)
    if budget_eur > 0 and spent >= budget_eur:
        raise HTTPException(status_code=402, detail=(
            f"KI-Monatsbudget erreicht ({spent:.2f} € / {budget_eur:.2f} €). "
            "Budget in den Einstellungen erhöhen."))

    label = f"To-do-Vorschläge: {customer.company or customer.name}"[:2000]
    try:
        result, usage = await customer_todo_ai.suggest_todos(
            context=context, hint=hint, model=model, api_key=api_key,
            open_titles=[t.title for t in open_todos], today=today)
    except HTTPException:
        raise
    except Exception as exc:
        db.add(AiLeadRun(brief=label, model=model, status="failed", error=str(exc)[:500]))
        raise HTTPException(status_code=502, detail=f"KI-Vorschlag fehlgeschlagen: {exc}")

    cost_usd = usage.cost_with(await get_pricing(model))
    cost_eur = round(cost_usd * await get_usd_eur_rate(), 4)
    db.add(AiLeadRun(brief=label, model=model, used_web_search=False,
                     cost_usd=round(cost_usd, 6), cost_eur=cost_eur,
                     candidates_found=len(result["suggestions"]), status="ok",
                     **usage.as_dict()))

    payload = json.dumps(result, ensure_ascii=False)
    if cache:
        cache.context_hash = wanted
        cache.payload = payload
    else:
        db.add(CustomerTodoSuggestion(customer_id=customer_id, context_hash=wanted,
                                      payload=payload))

    return TodoSuggestionResponse(
        suggestions=[TodoSuggestion(**s) for s in result["suggestions"]],
        ignored=result["ignored"], cached=False,
        run=AiRunCost(model=model, cost_usd=round(cost_usd, 6), cost_eur=cost_eur,
                      **usage.as_dict()),
        budget=ai_budget.budget_status(spent + cost_eur, budget_eur))
