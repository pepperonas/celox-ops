import uuid
from datetime import date as DateType
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class ComplianceRecord(OwnedMixin, Base):
    """Erfüllungsnachweis eines Pflicht-Rechtsdokuments für einen Kunden.

    Eine Zeile pro (Kunde, Vorlage). `signed_at` gesetzt = erfüllt. Erfüllt werden
    kann per Datei-Upload (method='upload', attachment_id verweist auf die Datei)
    oder manuell (method='manual')."""

    __tablename__ = "compliance_records"
    __table_args__ = (UniqueConstraint("customer_id", "template_id", name="uq_compliance_customer_template"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="CASCADE"), nullable=False
    )
    signed_at: Mapped[DateType | None] = mapped_column(Date, nullable=True)
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'upload' | 'manual'
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attachments.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
