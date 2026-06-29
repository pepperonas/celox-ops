import uuid
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class AppSettings(OwnedMixin, Base):
    """Single-row app-wide settings table (celox ops is single-user — no owner FK)."""

    __tablename__ = "app_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Default-Einzelpreis für neue Rechnungspositionen (auch KI-Import-Stundensatz).
    default_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("95"), server_default="95", nullable=False
    )
