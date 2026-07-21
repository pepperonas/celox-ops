"""Manuelle To-dos (owner-scoped) — anlegen, abhaken, verwalten.

Bezug optional auf Kunde ODER Lead. Die FK-Prüfung läuft über owner-scoped
Selects: `with_loader_criteria` versteckt fremde Zeilen nur beim SELECT, es
validiert keine Inserts (Tenancy-Invariante Nr. 3 in CLAUDE.md).
"""
import math
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.rainmaker_lead import RainmakerLead
from app.models.todo import Todo, TodoStatus
from app.schemas.todo import TodoCreate, TodoResponse, TodoToggle, TodoUpdate

router = APIRouter(
    prefix="/api/todos",
    tags=["todos"],
    dependencies=[Depends(get_current_user)],
)


async def _validate_refs(data, db: AsyncSession) -> None:
    """Kunde/Lead müssen dem aktuellen Owner gehören; höchstens einer von beiden."""
    if data.customer_id and data.lead_id:
        raise HTTPException(
            status_code=422,
            detail="Ein To-do kann entweder einem Kunden oder einem Lead zugeordnet werden, nicht beiden.",
        )
    if data.customer_id:
        found = (await db.execute(select(Customer.id).where(Customer.id == data.customer_id))).scalar_one_or_none()
        if not found:
            raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    if data.lead_id:
        found = (await db.execute(select(RainmakerLead.id).where(RainmakerLead.id == data.lead_id))).scalar_one_or_none()
        if not found:
            raise HTTPException(status_code=404, detail="Lead nicht gefunden")


async def _enrich(todos: list[Todo], db: AsyncSession) -> list[TodoResponse]:
    """Kunden-/Lead-Namen in einem Rutsch nachladen (kein N+1)."""
    customer_ids = {t.customer_id for t in todos if t.customer_id}
    lead_ids = {t.lead_id for t in todos if t.lead_id}

    customers: dict[uuid.UUID, str] = {}
    if customer_ids:
        rows = await db.execute(
            select(Customer.id, Customer.company, Customer.name).where(Customer.id.in_(customer_ids))
        )
        customers = {r.id: (r.company or "").strip() or r.name for r in rows}

    leads: dict[uuid.UUID, str] = {}
    if lead_ids:
        rows = await db.execute(
            select(RainmakerLead.id, RainmakerLead.company, RainmakerLead.contact_name).where(
                RainmakerLead.id.in_(lead_ids)
            )
        )
        leads = {r.id: (r.company or "").strip() or (r.contact_name or "") for r in rows}

    out = []
    for t in todos:
        resp = TodoResponse.model_validate(t)
        resp.customer_name = customers.get(t.customer_id) if t.customer_id else None
        resp.lead_name = leads.get(t.lead_id) if t.lead_id else None
        out.append(resp)
    return out


@router.get("")
async def list_todos(
    todo_status: TodoStatus | None = Query(None, alias="status"),
    customer_id: uuid.UUID | None = Query(None),
    lead_id: uuid.UUID | None = Query(None),
    overdue: bool = Query(False, description="Nur offene mit Fälligkeit in der Vergangenheit"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Todo)
    count_query = select(func.count()).select_from(Todo)

    conditions = []
    if todo_status is not None:
        conditions.append(Todo.status == todo_status)
    if customer_id:
        conditions.append(Todo.customer_id == customer_id)
    if lead_id:
        conditions.append(Todo.lead_id == lead_id)
    if overdue:
        conditions.append(Todo.status == TodoStatus.offen)
        conditions.append(Todo.due_date.is_not(None))
        conditions.append(Todo.due_date < date.today())
    if search:
        pattern = f"%{search}%"
        conditions.append(or_(Todo.title.ilike(pattern), Todo.notes.ilike(pattern)))

    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    # Offene zuerst, dann nach Fälligkeit (ohne Datum ans Ende), dann manuelle
    # Reihenfolge, dann jüngste zuerst.
    query = query.order_by(
        Todo.status.asc(),
        Todo.due_date.asc().nullslast(),
        Todo.sort_order.asc(),
        Todo.created_at.desc(),
    ).offset((page - 1) * page_size).limit(page_size)

    todos = (await db.execute(query)).scalars().all()

    return {
        "items": await _enrich(list(todos), db),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/stats")
async def todo_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Zähler für Dashboard-Karte und Übersicht."""
    today = date.today()
    row = (
        await db.execute(
            select(
                func.count().filter(Todo.status == TodoStatus.offen),
                func.count().filter(
                    Todo.status == TodoStatus.offen,
                    Todo.due_date.is_not(None),
                    Todo.due_date < today,
                ),
                func.count().filter(
                    Todo.status == TodoStatus.offen, Todo.due_date == today
                ),
            ).select_from(Todo)
        )
    ).one()
    return {"open": row[0] or 0, "overdue": row[1] or 0, "due_today": row[2] or 0}


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(data: TodoCreate, db: AsyncSession = Depends(get_db)) -> TodoResponse:
    await _validate_refs(data, db)
    todo = Todo(**data.model_dump())
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return (await _enrich([todo], db))[0]


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: uuid.UUID, data: TodoUpdate, db: AsyncSession = Depends(get_db)
) -> TodoResponse:
    todo = (await db.execute(select(Todo).where(Todo.id == todo_id))).scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="To-do nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    # Bezug nur prüfen, wenn er im Request steht (Presence-Check, damit ein
    # explizites null den Bezug löschen kann).
    if "customer_id" in update_data or "lead_id" in update_data:
        merged = type("Refs", (), {
            "customer_id": update_data.get("customer_id", todo.customer_id),
            "lead_id": update_data.get("lead_id", todo.lead_id),
        })
        await _validate_refs(merged, db)

    if "status" in update_data and update_data["status"] is not None:
        todo.done_at = (
            datetime.now(timezone.utc) if update_data["status"] == TodoStatus.erledigt else None
        )

    for key, value in update_data.items():
        setattr(todo, key, value)

    await db.flush()
    await db.refresh(todo)
    return (await _enrich([todo], db))[0]


@router.post("/{todo_id}/toggle", response_model=TodoResponse)
async def toggle_todo(
    todo_id: uuid.UUID, data: TodoToggle, db: AsyncSession = Depends(get_db)
) -> TodoResponse:
    """Abhaken bzw. wieder öffnen (idempotent — `done` ist das Ziel, kein Flip)."""
    todo = (await db.execute(select(Todo).where(Todo.id == todo_id))).scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="To-do nicht gefunden")

    todo.status = TodoStatus.erledigt if data.done else TodoStatus.offen
    todo.done_at = datetime.now(timezone.utc) if data.done else None
    await db.flush()
    await db.refresh(todo)
    return (await _enrich([todo], db))[0]


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    todo = (await db.execute(select(Todo).where(Todo.id == todo_id))).scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="To-do nicht gefunden")
    await db.delete(todo)
