import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class AiLeadRun(OwnedMixin, Base):
    """Protokoll eines KI-Lead-Such-Laufs — für die Kosten-Übersicht + Budget.
    Kosten werden exakt aus der Anthropic-`usage`-Antwort berechnet."""

    __tablename__ = "ai_lead_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(40), nullable=False)
    used_web_search: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    web_searches: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"), server_default="0", nullable=False)
    cost_eur: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"), server_default="0", nullable=False)

    candidates_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    leads_imported: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="ok", server_default="ok", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
