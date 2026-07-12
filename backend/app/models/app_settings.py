import uuid
from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
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
    # Pro-Nutzer-Präfix für Rechnungsnummern (z.B. "CO" → CO-2026-0001).
    invoice_prefix: Mapped[str] = mapped_column(
        String(10), default="CO", server_default="CO", nullable=False
    )
    # Pro-Workspace Google-Places-API-Key für die Lead-Suche (nullable = keiner
    # → Fallback auf die globale env-Variable GOOGLE_PLACES_API_KEY).
    google_places_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Eigener Nutzungszähler (Google gibt das Restkontingent per Key nicht her).
    google_places_calls: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    google_places_period: Mapped[str | None] = mapped_column(String(7), nullable=True)  # "YYYY-MM"
