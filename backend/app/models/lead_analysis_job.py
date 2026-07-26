import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
ERROR = "error"


class LeadAnalysisJob(OwnedMixin, Base):
    """Auftrag für die automatische Website-Analyse eines Leads.

    Bewusst eine eigene Tabelle (auto via `create_all`, **keine Migration**) statt
    eines Status-Feldes am Lead: sie überlebt Neustarts, hält die Fehlermeldung
    fest und lässt sich reihen/wiederholen. Der Worker läuft in-process (wie der
    stündliche Cron) und scopet pro Job auf `owner_id`.
    """

    __tablename__ = "lead_analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default=QUEUED, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
