import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.invoice import InvoiceStatus


class InvoicePosition(BaseModel):
    position: int
    beschreibung: str
    menge: Decimal
    einheit: str = "Stk"
    einzelpreis: Decimal
    gesamt: Decimal


class InvoiceBase(BaseModel):
    customer_id: uuid.UUID
    order_id: uuid.UUID | None = None
    contract_id: uuid.UUID | None = None
    title: str
    positions: list[InvoicePosition]
    tax_rate: Decimal = Decimal("19.00")
    invoice_date: date
    due_date: date
    notes: str | None = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    contract_id: uuid.UUID | None = None
    title: str | None = None
    positions: list[InvoicePosition] | None = None
    tax_rate: Decimal | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    notes: str | None = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    order_id: uuid.UUID | None = None
    contract_id: uuid.UUID | None = None
    invoice_number: str
    title: str
    positions: list[InvoicePosition]
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    pdf_path: str | None = None
    notes: str | None = None
    customer_name: str = ""
    created_at: datetime
    updated_at: datetime


class InvoiceDetail(InvoiceResponse):
    pass


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


class QuickInvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    beschreibung: str
    menge: Decimal = Decimal("1")
    einheit: str = "pauschal"
    einzelpreis: Decimal
    notes: str | None = None
