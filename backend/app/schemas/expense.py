import uuid
from datetime import date as DateType
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.expense import ExpenseCategory


class ExpenseBase(BaseModel):
    description: str
    category: ExpenseCategory
    amount: Decimal
    date: DateType
    vendor: str | None = None
    recurring: bool = False
    notes: str | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    description: str | None = None
    category: ExpenseCategory | None = None
    amount: Decimal | None = None
    date: DateType | None = None
    vendor: str | None = None
    recurring: bool | None = None
    notes: str | None = None


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
