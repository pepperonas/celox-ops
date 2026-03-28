import math
import uuid

import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from pydantic import BaseModel as PydanticBaseModel

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.activity import Activity
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderDetail, OrderResponse, OrderUpdate
from app.services.email_service import send_email
from app.services.pdf_service import generate_quote_pdf


class EmailRequest(PydanticBaseModel):
    to_email: str
    subject: str | None = None
    message: str | None = None

router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_orders(
    customer_id: uuid.UUID | None = Query(None),
    order_status: OrderStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Order).options(joinedload(Order.customer))
    count_query = select(func.count()).select_from(Order)

    if customer_id:
        query = query.where(Order.customer_id == customer_id)
        count_query = count_query.where(Order.customer_id == customer_id)
    if order_status:
        query = query.where(Order.status == order_status)
        count_query = count_query.where(Order.status == order_status)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Order, sort_by, Order.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().unique().all()

    responses = []
    for order in orders:
        resp = OrderResponse.model_validate(order)
        resp.customer_name = order.customer.name if order.customer else ""
        responses.append(resp)

    return {
        "items": responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OrderDetail:
    result = await db.execute(
        select(Order)
        .options(joinedload(Order.customer), joinedload(Order.invoices))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")

    detail = OrderDetail.model_validate(order)
    detail.customer_name = order.customer.name if order.customer else ""
    detail.invoices_count = len(order.invoices)
    return detail


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    # Verify customer exists
    cust = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    order = Order(**data.model_dump())
    db.add(order)
    await db.flush()
    await db.refresh(order)

    activity = Activity(
        customer_id=data.customer_id,
        type="order",
        title=f"Auftrag erstellt: {data.title}",
        description=f"Status: {order.status.value}" if hasattr(order.status, 'value') else None,
    )
    db.add(activity)

    resp = OrderResponse.model_validate(order)
    resp.customer_name = customer.name
    return resp


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    result = await db.execute(
        select(Order).options(joinedload(Order.customer)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    await db.flush()
    await db.refresh(order)

    # Re-fetch with customer
    result = await db.execute(
        select(Order).options(joinedload(Order.customer)).where(Order.id == order_id)
    )
    order = result.scalar_one()

    resp = OrderResponse.model_validate(order)
    resp.customer_name = order.customer.name if order.customer else ""
    return resp


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    await db.delete(order)


@router.post("/{order_id}/generate-quote-pdf")
async def generate_quote_pdf_endpoint(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Order).options(joinedload(Order.customer)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    if order.status != OrderStatus.angebot:
        raise HTTPException(
            status_code=400,
            detail="Angebots-PDF kann nur für Aufträge im Status 'Angebot' erstellt werden",
        )
    customer = order.customer
    if not customer:
        raise HTTPException(status_code=400, detail="Kein Kunde zugeordnet")

    pdf_path = generate_quote_pdf(order, customer)
    order.quote_pdf_path = pdf_path
    await db.flush()
    await db.refresh(order)

    return {"quote_pdf_path": pdf_path}


@router.post("/{order_id}/send-quote-email")
async def send_quote_email(
    order_id: uuid.UUID,
    data: EmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Angebot per E-Mail senden."""
    result = await db.execute(
        select(Order)
        .options(joinedload(Order.customer))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    if not order.quote_pdf_path or not os.path.isfile(order.quote_pdf_path):
        raise HTTPException(status_code=400, detail="Angebots-PDF wurde noch nicht generiert.")

    customer = order.customer

    subject = data.subject or f"Angebot — {order.title} — {settings.BUSINESS_NAME}"

    if data.message:
        body_html = data.message.replace("\n", "<br>")
    else:
        customer_name = customer.name if customer else "Kunde"
        body_html = (
            f"Sehr geehrte Damen und Herren,<br><br>"
            f"anbei erhalten Sie unser Angebot <strong>{order.title}</strong>.<br><br>"
            f"Wir würden uns freuen, Sie als Kunden begrüßen zu dürfen. "
            f"Bei Fragen stehen wir Ihnen gerne zur Verfügung.<br><br>"
            f"Mit freundlichen Grüßen<br>"
            f"{settings.BUSINESS_OWNER}<br>"
            f"{settings.BUSINESS_NAME}"
        )

    try:
        await send_email(
            to_email=data.to_email,
            subject=subject,
            body_html=body_html,
            pdf_path=order.quote_pdf_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"E-Mail-Versand fehlgeschlagen: {e}")

    return {"success": True, "message": f"Angebot wurde an {data.to_email} gesendet."}


@router.get("/{order_id}/quote-pdf")
async def download_quote_pdf(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    if not order.quote_pdf_path or not os.path.isfile(order.quote_pdf_path):
        raise HTTPException(status_code=404, detail="Angebots-PDF nicht gefunden")

    filename = os.path.basename(order.quote_pdf_path)
    return FileResponse(
        order.quote_pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
