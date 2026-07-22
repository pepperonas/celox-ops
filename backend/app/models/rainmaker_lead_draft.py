import hashlib
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


def lead_email_hash(lead, model: str) -> str:
    """Stabiler Content-Hash der mail-relevanten Lead-Felder + Modell.

    Rein + testbar. Ändert sich eines dieser Felder, wird der Cache verworfen
    und neu generiert — sonst würde ein veralteter Entwurf ausgeliefert."""
    def s(x):
        return "" if x in (None, "") else str(x).strip()

    tags = getattr(lead, "tags", None) or []
    parts = [
        model,
        s(getattr(lead, "company", None)),
        s(getattr(lead, "contact_name", None)),
        s(getattr(lead, "role", None)),
        s(getattr(lead, "decision_maker", None)),
        s(getattr(lead, "target", None)),
        s(getattr(lead, "employee_count", None)),
        s(getattr(lead, "website", None)),
        s(getattr(lead, "notes", None)),
        "|".join(str(t) for t in tags),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


class RainmakerLeadDraft(OwnedMixin, Base):
    """Zwischengespeicherter KI-Mailentwurf pro Lead — spart Tokens: unveränderte
    Leads liefern denselben Entwurf ohne erneuten KI-Call. Ein Datensatz je Lead
    (unique), wird beim Regenerieren/Feldänderung überschrieben."""

    __tablename__ = "rainmaker_lead_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    product: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
