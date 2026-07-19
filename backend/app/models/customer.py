import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app.tenancy import OwnedMixin


class Base(DeclarativeBase):
    pass


class Customer(OwnedMixin, Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_tracker_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_repos: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Handoff-Status je Ziel-App als JSON (Kontrakt §6.4) — nur server-seitig
    # geschrieben (routers/handoff.py), nie vom Client. Bestehende DBs brauchen
    # ein manuelles ALTER TABLE (scripts/add_customer_handoff.sql).
    portal_handoff: Mapped[str | None] = mapped_column(Text, nullable=True)
    datenschutz_handoff: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships are NOT eager-loaded by default — opt-in via joinedload()
    # in the specific endpoint that needs them.
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order", back_populates="customer", lazy="raise"
    )
    contracts: Mapped[list["Contract"]] = relationship(  # noqa: F821
        "Contract", back_populates="customer", lazy="raise"
    )
    invoices: Mapped[list["Invoice"]] = relationship(  # noqa: F821
        "Invoice", back_populates="customer", lazy="raise"
    )
