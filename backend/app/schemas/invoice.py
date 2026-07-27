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
    tax_exempt: bool = False
    invoice_date: date
    due_date: date
    notes: str | None = None
    special_terms: str | None = None
    service_description: str | None = None
    token_usage_from: date | None = None
    token_usage_to: date | None = None
    github_commits_from: date | None = None
    github_commits_to: date | None = None
    selected_tracker_urls: str | None = None
    selected_github_repos: str | None = None
    include_activity_chart: bool = False
    discount_type: str | None = None
    discount_value: float | None = None
    discount_reason: str | None = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    contract_id: uuid.UUID | None = None
    title: str | None = None
    positions: list[InvoicePosition] | None = None
    tax_rate: Decimal | None = None
    tax_exempt: bool | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    special_terms: str | None = None
    service_description: str | None = None
    token_usage_from: date | None = None
    token_usage_to: date | None = None
    github_commits_from: date | None = None
    github_commits_to: date | None = None
    selected_tracker_urls: str | None = None
    selected_github_repos: str | None = None
    include_activity_chart: bool = False
    discount_type: str | None = None
    discount_value: float | None = None
    discount_reason: str | None = None


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
    tax_exempt: bool = False
    tax_amount: Decimal
    total: Decimal
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    pdf_path: str | None = None
    notes: str | None = None
    special_terms: str | None = None
    service_description: str | None = None
    token_usage_from: date | None = None
    token_usage_to: date | None = None
    github_commits_from: date | None = None
    github_commits_to: date | None = None
    selected_tracker_urls: str | None = None
    selected_github_repos: str | None = None
    include_activity_chart: bool = False
    discount_type: str | None = None
    discount_value: float | None = None
    discount_reason: str | None = None
    reminder_level: int = 0
    reminder_sent_at: datetime | None = None
    reminder_pdf_path: str | None = None
    amount_paid: Decimal = Decimal("0")
    is_credit_note: bool = False
    credit_note_for: uuid.UUID | None = None
    credit_note_for_number: str | None = None
    # Rückrichtung (Original → Gutschrift): nur im Detail-Endpoint gefüllt.
    credit_note_id: uuid.UUID | None = None
    credit_note_number: str | None = None
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


# --------------------------------------------------------------------------- #
#  Kontoauszug-Import (Zahlungsabgleich)
# --------------------------------------------------------------------------- #
class BankMatchProposal(BaseModel):
    """Ein Zuordnungsvorschlag Buchung -> Rechnung. Wird nie automatisch gebucht."""
    invoice_id: uuid.UUID
    invoice_number: str
    customer_name: str = ""
    invoice_total: Decimal
    invoice_open: Decimal
    amount: Decimal
    confidence: str          # exact | number | amount
    reason: str
    booking_date: str
    purpose: str = ""
    counterparty: str | None = None


class BankUnmatched(BaseModel):
    booking_date: str
    amount: Decimal
    purpose: str = ""
    counterparty: str | None = None
    reason: str


class BankImportPreview(BaseModel):
    proposals: list[BankMatchProposal] = []
    unmatched: list[BankUnmatched] = []
    ignored_debits: int = 0
    transactions_total: int = 0
    open_invoices: int = 0


class BankImportApplyRequest(BaseModel):
    rows: list[BankMatchProposal]


class BankAppliedRow(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    amount: Decimal
    # Stand VOR der Buchung -> ermoeglicht das bestehende Undo
    # (PUT /invoices/{id}/payment-state).
    previous_amount_paid: Decimal
    previous_status: InvoiceStatus
    new_status: InvoiceStatus


class BankImportResult(BaseModel):
    applied: list[BankAppliedRow] = []
    skipped: list[str] = []


class PaymentStateRestore(BaseModel):
    """Undo-Payload: setzt Zahlungsstand + Status auf einen früheren Stand
    zurück (z. B. nach versehentlichem Bulk-„Als bezahlt")."""
    amount_paid: Decimal
    status: InvoiceStatus
