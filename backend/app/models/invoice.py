import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.customer import Base


class InvoiceStatus(str, enum.Enum):
    entwurf = "entwurf"
    gestellt = "gestellt"
    bezahlt = "bezahlt"
    ueberfaellig = "ueberfaellig"
    storniert = "storniert"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    invoice_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    positions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("19.00")
    )
    tax_exempt: Mapped[bool] = mapped_column(default=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.entwurf, nullable=False
    )
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    token_usage_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    github_commits_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    github_commits_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    selected_tracker_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_github_repos: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_activity_chart: Mapped[bool] = mapped_column(default=False)
    discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reminder_level: Mapped[int] = mapped_column(Integer, default=0)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), server_default="0")
    credit_note_for: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True
    )
    is_credit_note: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship(  # noqa: F821
        "Customer", back_populates="invoices"
    )
    order: Mapped["Order | None"] = relationship(  # noqa: F821
        "Order", back_populates="invoices"
    )
    contract: Mapped["Contract | None"] = relationship(  # noqa: F821
        "Contract", back_populates="invoices"
    )
