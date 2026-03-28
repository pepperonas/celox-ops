import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.expense import Expense, ExpenseCategory
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)

router = APIRouter(
    prefix="/api/expenses",
    tags=["expenses"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_expenses(
    search: str | None = Query(None),
    category: str | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("date"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Expense)
    count_query = select(func.count()).select_from(Expense)

    if search:
        search_filter = f"%{search}%"
        condition = (
            Expense.description.ilike(search_filter)
            | Expense.vendor.ilike(search_filter)
            | Expense.notes.ilike(search_filter)
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    if category:
        query = query.where(Expense.category == category)
        count_query = count_query.where(Expense.category == category)

    if date_from:
        query = query.where(Expense.date >= date_from)
        count_query = count_query.where(Expense.date >= date_from)

    if date_to:
        query = query.where(Expense.date <= date_to)
        count_query = count_query.where(Expense.date <= date_to)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Expense, sort_by, Expense.date)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    expenses = result.scalars().all()

    return {
        "items": [ExpenseResponse.model_validate(e) for e in expenses],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/summary")
async def expense_summary(
    year: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Totals grouped by category and month for a given year."""
    # By category
    cat_query = (
        select(Expense.category, func.sum(Expense.amount).label("total"))
        .where(extract("year", Expense.date) == year)
        .group_by(Expense.category)
    )
    cat_result = await db.execute(cat_query)
    by_category = [
        {"category": row.category.value, "total": float(row.total)}
        for row in cat_result.all()
    ]

    # By month
    month_query = (
        select(
            extract("month", Expense.date).label("month"),
            func.sum(Expense.amount).label("total"),
        )
        .where(extract("year", Expense.date) == year)
        .group_by(extract("month", Expense.date))
        .order_by(extract("month", Expense.date))
    )
    month_result = await db.execute(month_query)
    by_month = [
        {"month": int(row.month), "total": float(row.total)}
        for row in month_result.all()
    ]

    # Grand total
    total_query = select(func.sum(Expense.amount)).where(
        extract("year", Expense.date) == year
    )
    total_result = await db.execute(total_query)
    grand_total = total_result.scalar_one_or_none() or 0

    return {
        "year": year,
        "total": float(grand_total),
        "by_category": by_category,
        "by_month": by_month,
    }


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
    return ExpenseResponse.model_validate(expense)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    expense = Expense(**data.model_dump())
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(expense, key, value)

    await db.flush()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
    await db.delete(expense)
