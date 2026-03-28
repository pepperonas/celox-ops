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

from app.models.customer import Base


class ContractType(str, enum.Enum):
    hosting = "hosting"
    wartung = "wartung"
    support = "support"
    sonstige = "sonstige"


class BillingCycle(str, enum.Enum):
    monatlich = "monatlich"
    quartalsweise = "quartalsweise"
    halbjaehrlich = "halbjaehrlich"
    jaehrlich = "jaehrlich"


class ContractStatus(str, enum.Enum):
    aktiv = "aktiv"
    gekuendigt = "gekuendigt"
    ausgelaufen = "ausgelaufen"


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ContractType] = mapped_column(
        Enum(ContractType), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle), default=BillingCycle.monatlich, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.aktiv, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship(  # noqa: F821
        "Customer", back_populates="contracts"
    )
    invoices: Mapped[list["Invoice"]] = relationship(  # noqa: F821
        "Invoice", back_populates="contract", lazy="selectin"
    )
