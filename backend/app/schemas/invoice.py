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
    token_usage_from: date | None = None
    token_usage_to: date | None = None


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
    token_usage_from: date | None = None
    token_usage_to: date | None = None


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
    token_usage_from: date | None = None
    token_usage_to: date | None = None
    reminder_level: int = 0
    reminder_sent_at: datetime | None = None
    reminder_pdf_path: str | None = None
    amount_paid: Decimal = Decimal("0")
    is_credit_note: bool = False
    credit_note_for: uuid.UUID | None = None
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


class PaymentRequest(BaseModel):
    amount: Decimal
