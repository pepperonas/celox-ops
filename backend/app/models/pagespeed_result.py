import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.customer import Base


class PagespeedResult(Base):
    __tablename__ = "pagespeed_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    strategy: Mapped[str] = mapped_column(String(10), nullable=False, default="mobile")
    score_performance: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_accessibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_best_practices: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_seo: Mapped[float | None] = mapped_column(Float, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_scores: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped["Customer"] = relationship("Customer")  # noqa: F821
