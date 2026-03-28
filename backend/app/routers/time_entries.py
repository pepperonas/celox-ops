import math
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.time_entry import TimeEntry
from app.schemas.time_entry import (
    TimeEntryCreate,
    TimeEntryResponse,
    TimeEntrySummary,
    TimeEntryUpdate,
)

router = APIRouter(
    prefix="/api/time-entries",
    tags=["time-entries"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
) -> list[TimeEntrySummary]:
    query = (
        select(
            TimeEntry.customer_id,
            Customer.name.label("customer_name"),
            func.sum(TimeEntry.hours).label("total_hours"),
            func.sum(
                case(
                    (
                        TimeEntry.hourly_rate.is_not(None),
                        TimeEntry.hours * TimeEntry.hourly_rate,
                    ),
                    else_=Decimal("0"),
                )
            ).label("total_amount"),
            func.sum(
                case(
                    (TimeEntry.invoiced == False, TimeEntry.hours),  # noqa: E712
                    else_=Decimal("0"),
                )
            ).label("uninvoiced_hours"),
        )
        .join(Customer, TimeEntry.customer_id == Customer.id)
        .group_by(TimeEntry.customer_id, Customer.name)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        TimeEntrySummary(
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            total_hours=row.total_hours or Decimal("0"),
            total_amount=row.total_amount or Decimal("0"),
            uninvoiced_hours=row.uninvoiced_hours or Decimal("0"),
        )
        for row in rows
    ]


@router.get("")
async def list_time_entries(
    customer_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    invoiced: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(TimeEntry).options(joinedload(TimeEntry.customer))
    count_query = select(func.count()).select_from(TimeEntry)

    if customer_id:
        query = query.where(TimeEntry.customer_id == customer_id)
        count_query = count_query.where(TimeEntry.customer_id == customer_id)
    if date_from:
        query = query.where(TimeEntry.date >= date_from)
        count_query = count_query.where(TimeEntry.date >= date_from)
    if date_to:
        query = query.where(TimeEntry.date <= date_to)
        count_query = count_query.where(TimeEntry.date <= date_to)
    if invoiced is not None:
        query = query.where(TimeEntry.invoiced == invoiced)
        count_query = count_query.where(TimeEntry.invoiced == invoiced)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(TimeEntry.date.desc(), TimeEntry.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    entries = result.unique().scalars().all()

    items = []
    for e in entries:
        resp = TimeEntryResponse.model_validate(e)
        resp.customer_name = e.customer.name if e.customer else None
        items.append(resp)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.post("", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    data: TimeEntryCreate,
    db: AsyncSession = Depends(get_db),
) -> TimeEntryResponse:
    # Verify customer exists
    cust = await db.execute(select(Customer).where(Customer.id == data.customer_id))
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    entry = TimeEntry(**data.model_dump())
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    resp = TimeEntryResponse.model_validate(entry)
    resp.customer_name = customer.name
    return resp


@router.put("/{entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    entry_id: uuid.UUID,
    data: TimeEntryUpdate,
    db: AsyncSession = Depends(get_db),
) -> TimeEntryResponse:
    result = await db.execute(
        select(TimeEntry)
        .options(joinedload(TimeEntry.customer))
        .where(TimeEntry.id == entry_id)
    )
    entry = result.unique().scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Zeiteintrag nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.flush()
    await db.refresh(entry)

    # Re-load customer if customer_id changed
    if "customer_id" in update_data:
        cust = await db.execute(
            select(Customer).where(Customer.id == entry.customer_id)
        )
        customer = cust.scalar_one_or_none()
    else:
        customer = entry.customer

    resp = TimeEntryResponse.model_validate(entry)
    resp.customer_name = customer.name if customer else None
    return resp


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(TimeEntry).where(TimeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Zeiteintrag nicht gefunden")

    await db.delete(entry)
