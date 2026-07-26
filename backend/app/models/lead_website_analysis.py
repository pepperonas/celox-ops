import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class LeadWebsiteAnalysis(OwnedMixin, Base):
    """Eine (versionierte) Website-Analyse eines Leads — volle Historie (A1).

    Ein Datensatz pro Analyse-Lauf; die Lead-Liste liest denormalisierte
    Zusammenfassungsfelder direkt am `RainmakerLead` (web_score/web_rating/…).
    Owner-scoped via OwnedMixin.
    """

    __tablename__ = "lead_website_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    analysis_version: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[str] = mapped_column(String(10), nullable=False)  # gruen/gelb/orange/rot
    has_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    technologies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Tiefenanalyse (A2, opt-in) — NULL, wenn nicht mitgelaufen.
    # Bestehende DBs: manuelles ALTER (scripts/add_lead_web_analysis_deep.sql).
    ai_review: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pagespeed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
