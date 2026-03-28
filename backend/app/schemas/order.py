import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderBase(BaseModel):
    customer_id: uuid.UUID
    title: str
    description: str | None = None
    status: OrderStatus = OrderStatus.angebot
    amount: Decimal | None = None
    hourly_rate: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    positions: list | None = None
    valid_until: date | None = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    title: str | None = None
    description: str | None = None
    status: OrderStatus | None = None
    amount: Decimal | None = None
    hourly_rate: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    positions: list | None = None
    valid_until: date | None = None


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_name: str = ""
    quote_pdf_path: str | None = None
    created_at: datetime
    updated_at: datetime


class OrderDetail(OrderResponse):
    invoices_count: int = 0
