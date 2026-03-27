import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetail,
    InvoiceResponse,
    InvoiceStatusUpdate,
    InvoiceUpdate,
    QuickInvoiceCreate,
)
from app.services.invoice_service import calculate_invoice_totals, generate_invoice_number
from app.services.pdf_service import generate_invoice_pdf

router = APIRouter(
    prefix="/api/invoices",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_invoices(
    customer_id: uuid.UUID | None = Query(None),
    invoice_status: InvoiceStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Invoice).options(joinedload(Invoice.customer))
    count_query = select(func.count()).select_from(Invoice)

    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
        count_query = count_query.where(Invoice.customer_id == customer_id)
    if invoice_status:
        query = query.where(Invoice.status == invoice_status)
        count_query = count_query.where(Invoice.status == invoice_status)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Invoice, sort_by, Invoice.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    invoices = result.scalars().unique().all()

    responses = []
    for inv in invoices:
        resp = InvoiceResponse.model_validate(inv)
        resp.customer_name = inv.customer.name if inv.customer else ""
        responses.append(resp)

    return {
        "items": responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceDetail:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    detail = InvoiceDetail.model_validate(invoice)
    detail.customer_name = invoice.customer.name if invoice.customer else ""
    return detail


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    # Verify customer
    cust = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    invoice_number = await generate_invoice_number(db)

    positions_dicts = [p.model_dump() for p in data.positions]
    # Convert Decimal to str for JSON serialization
    positions_json = []
    for p in positions_dicts:
        positions_json.append({
            k: str(v) if hasattr(v, "quantize") else v
            for k, v in p.items()
        })

    subtotal, tax_amount, total = calculate_invoice_totals(
        positions_dicts, data.tax_rate, settings.KLEINUNTERNEHMER
    )

    invoice = Invoice(
        customer_id=data.customer_id,
        order_id=data.order_id,
        contract_id=data.contract_id,
        invoice_number=invoice_number,
        title=data.title,
        positions=positions_json,
        subtotal=subtotal,
        tax_rate=data.tax_rate,
        tax_amount=tax_amount,
        total=total,
        invoice_date=data.invoice_date,
        due_date=data.due_date,
        notes=data.notes,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = customer.name
    return resp


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)

    if "positions" in update_data and update_data["positions"] is not None:
        positions_dicts = [p.model_dump() for p in data.positions]  # type: ignore[union-attr]
        positions_json = []
        for p in positions_dicts:
            positions_json.append({
                k: str(v) if hasattr(v, "quantize") else v
                for k, v in p.items()
            })
        update_data["positions"] = positions_json

        tax_rate = data.tax_rate if data.tax_rate is not None else invoice.tax_rate
        subtotal, tax_amount, total = calculate_invoice_totals(
            positions_dicts, tax_rate, settings.KLEINUNTERNEHMER
        )
        update_data["subtotal"] = subtotal
        update_data["tax_amount"] = tax_amount
        update_data["total"] = total

    for key, value in update_data.items():
        setattr(invoice, key, value)

    await db.flush()
    await db.refresh(invoice)

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one()

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.put("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: uuid.UUID,
    data: InvoiceStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    invoice.status = data.status
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.post("/{invoice_id}/generate-pdf", response_model=InvoiceResponse)
async def generate_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    pdf_path = generate_invoice_pdf(invoice, invoice.customer)
    invoice.pdf_path = pdf_path
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.get("/{invoice_id}/pdf")
async def download_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if not invoice.pdf_path:
        raise HTTPException(status_code=404, detail="PDF wurde noch nicht generiert")

    return FileResponse(
        path=invoice.pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.post("/quick", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def quick_invoice(
    data: QuickInvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Schnellrechnung: Eine Position, keine Auftrags-/Vertragsverknüpfung."""
    cust = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    invoice_number = await generate_invoice_number(db)

    from datetime import date, timedelta
    from decimal import Decimal

    gesamt = data.menge * data.einzelpreis
    positions_json = [{
        "position": 1,
        "beschreibung": data.beschreibung,
        "menge": str(data.menge),
        "einheit": data.einheit,
        "einzelpreis": str(data.einzelpreis),
        "gesamt": str(gesamt),
    }]

    subtotal = gesamt
    if settings.KLEINUNTERNEHMER:
        tax_amount = Decimal("0")
        tax_rate = Decimal("0")
    else:
        tax_rate = Decimal("19.00")
        tax_amount = subtotal * tax_rate / Decimal("100")
    total = subtotal + tax_amount

    today = date.today()
    invoice = Invoice(
        customer_id=data.customer_id,
        invoice_number=invoice_number,
        title=data.beschreibung,
        positions=positions_json,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
        invoice_date=today,
        due_date=today + timedelta(days=14),
        notes=data.notes,
        status=InvoiceStatus.entwurf,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = customer.name
    return resp


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if invoice.status != InvoiceStatus.entwurf:
        raise HTTPException(
            status_code=400,
            detail="Nur Rechnungen im Status 'Entwurf' können gelöscht werden",
        )
    await db.delete(invoice)
