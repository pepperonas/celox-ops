import uuid
from datetime import date as DateType
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.todo import TodoPriority, TodoStatus


class TodoBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    due_date: DateType | None = None
    priority: TodoPriority = TodoPriority.normal


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = None
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    due_date: DateType | None = None
    priority: TodoPriority | None = None
    status: TodoStatus | None = None
    sort_order: int | None = None


class TodoResponse(TodoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: TodoStatus
    done_at: datetime | None = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime
    # Angereichert im Router (Anzeige ohne Zweitabfrage im Client)
    customer_name: str | None = None
    lead_name: str | None = None


class TodoToggle(BaseModel):
    """Explizites Ziel statt Umschalten — verhindert, dass ein doppelter Klick
    (oder ein Retry nach Timeout) das To-do wieder öffnet."""
    done: bool
