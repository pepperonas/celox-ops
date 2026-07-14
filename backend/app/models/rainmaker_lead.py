import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Computed, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func, text,
)
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.customer import Base
from app.tenancy import OwnedMixin

# Normalisierungs-SQL für die generierten Dedup-Spalten. MUSS deckungsgleich mit
# services/lead_dedup.py::norm_email/norm_website sein — sonst greifen die
# Unique-Indizes woanders als der App-Code.
_EMAIL_NORM_SQL = "nullif(lower(btrim(email)), '')"
_WEBSITE_NORM_SQL = (
    "nullif(btrim(rtrim("
    "regexp_replace(regexp_replace(lower(btrim(website)), '^https?://', '', 'i'),"
    " '^www\\.', '', 'i'), '/')), '')"
)


class RainmakerLeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"          # angeschrieben, Annahme/Antwort steht aus
    connected = "connected"          # LinkedIn: Anfrage angenommen (vernetzt)
    in_conversation = "in_conversation"
    proposal = "proposal"
    won = "won"
    lost = "lost"
    dormant = "dormant"


class RainmakerPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


# Statuses that count as "closed" — a lead in these states does NOT require a
# planned next action (the anti-stalling rule in the activation engine).
CLOSED_STATUSES = {
    RainmakerLeadStatus.won,
    RainmakerLeadStatus.lost,
    RainmakerLeadStatus.dormant,
}


class RainmakerLead(OwnedMixin, Base):
    __tablename__ = "rainmaker_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # E-Mail-Qualitätsurteil (services/email_verifier.py): valid/role/disposable/
    # no_mx/invalid_syntax/unknown/None(=ungeprüft). SMTP-frei.
    email_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[RainmakerLeadStatus] = mapped_column(
        Enum(RainmakerLeadStatus, native_enum=False, length=20),
        default=RainmakerLeadStatus.new,
        server_default="new",
        nullable=False,
    )
    priority: Mapped[RainmakerPriority] = mapped_column(
        Enum(RainmakerPriority, native_enum=False, length=10),
        default=RainmakerPriority.medium,
        server_default="medium",
        nullable=False,
    )
    value_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Verknüpfter Kunde nach Lead→Kunde-Konvertierung (nullable).
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Stored as a JSON array of strings.
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Generierte, normalisierte Dedup-Schlüssel (read-only) — treiben die
    # partiellen Unique-Indizes (race-sicher gegen parallele Importe).
    email_norm: Mapped[str | None] = mapped_column(
        Text, Computed(_EMAIL_NORM_SQL, persisted=True), nullable=True
    )
    website_norm: Mapped[str | None] = mapped_column(
        Text, Computed(_WEBSITE_NORM_SQL, persisted=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    activities: Mapped[list["RainmakerActivity"]] = relationship(  # noqa: F821
        "RainmakerActivity",
        back_populates="lead",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="RainmakerActivity.created_at",
    )

    __table_args__ = (
        # Pro Owner: keine zwei Leads mit gleicher E-Mail bzw. gleicher Website.
        # Partiell (nur wo der Schlüssel gesetzt ist) → viele NULLs bleiben erlaubt.
        Index(
            "uq_rainmaker_lead_owner_email", "owner_id", "email_norm",
            unique=True, postgresql_where=text("email_norm IS NOT NULL"),
        ),
        Index(
            "uq_rainmaker_lead_owner_website", "owner_id", "website_norm",
            unique=True, postgresql_where=text("website_norm IS NOT NULL"),
        ),
    )
