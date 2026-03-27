import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderDetail, OrderResponse, OrderUpdate

router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    customer_id: uuid.UUID | None = Query(None),
    order_status: OrderStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    query = select(Order).options(joinedload(Order.customer))

    if customer_id:
        query = query.where(Order.customer_id == customer_id)
    if order_status:
        query = query.where(Order.status == order_status)

    sort_column = getattr(Order, sort_by, Order.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().unique().all()

    responses = []
    for order in orders:
        resp = OrderResponse.model_validate(order)
        resp.customer_name = order.customer.name if order.customer else ""
        responses.append(resp)
    return responses


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
