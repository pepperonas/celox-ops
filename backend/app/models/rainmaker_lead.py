import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.customer import Base
from app.tenancy import OwnedMixin


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
    # Stored as a JSON array of strings.
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
