import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetail,
    CustomerResponse,
    CustomerUpdate,
)

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_customers(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
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
