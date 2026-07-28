import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class ExpenseCategory(str, enum.Enum):
    hosting = "hosting"
    domain = "domain"
    software = "software"
    lizenz = "lizenz"
    hardware = "hardware"
    ki_api = "ki_api"
    werbung = "werbung"
    buero = "buero"
    reise = "reise"
    sonstige = "sonstige"


class Expense(OwnedMixin, Base):
    __tablename__ = "expenses"
    # ACHTUNG: EIN __table_args__ pro Klasse — eine zweite Zuweisung würde die
    # erste stillschweigend überschreiben (Python-Klassenkörper, letzte gewinnt).
    __table_args__ = (
        Index("idx_expenses_date", "date"),
        # Pro Arbeitsbereich darf ein Herkunftsschlüssel nur einmal vorkommen.
        # Partiell, damit handgepflegte Ausgaben (external_ref NULL) unbegrenzt
        # erlaubt bleiben.
        Index("uq_expense_owner_external_ref", "owner_id", "external_ref",
              unique=True, postgresql_where=text("external_ref IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Herkunftsschlüssel für Importe (z. B. "hostinger:<abo-id>:<datum>"). Macht
    # den Import idempotent: derselbe Abrechnungszeitraum desselben Abos kann
    # nicht zweimal als Ausgabe landen. NULL bei handgepflegten Ausgaben.
    # Bestehende DBs: manuelles ALTER (scripts/add_expense_external_ref.sql).
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
