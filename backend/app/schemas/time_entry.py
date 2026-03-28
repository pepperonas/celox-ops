import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TimeEntryBase(BaseModel):
    customer_id: uuid.UUID
    description: str
    date: date
    hours: Decimal
    hourly_rate: Decimal | None = None
    notes: str | None = None


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    description: str | None = None
    date: date | None = None
    hours: Decimal | None = None
    hourly_rate: Decimal | None = None
    notes: str | None = None
    invoiced: bool | None = None


class TimeEntryResponse(TimeEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoiced: bool
    created_at: datetime
    customer_name: str | None = None


class TimeEntrySummary(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    total_hours: Decimal
    total_amount: Decimal
    uninvoiced_hours: Decimal
