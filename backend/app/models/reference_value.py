import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class ReferenceValue(OwnedMixin, Base):
    """Selbst-erstellter, feldbezogener Referenzwert/Tag (Phase B2).

    Werte leben weiter als Freitext/JSON in den Records — diese Tabelle hält
    zusätzlich eigene, evtl. noch ungenutzte Werte (mit Erstellungsdatum) und ist
    die Verwaltungs-Quelle. Kuratierte Taxonomie-Werte stehen NICHT hier drin
    (die kommen aus `services/taxonomy.py`). Owner-scoped via OwnedMixin.
    """

    __tablename__ = "reference_values"
    __table_args__ = (
        Index("ix_reference_values_owner_field", "owner_id", "field"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
