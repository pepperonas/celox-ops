import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, text
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
    # Anthropic-API-Key **pro Arbeitsbereich**: jeder Bereichs-Inhaber rechnet
    # über seinen eigenen Schlüssel ab. Mitarbeitende haben keinen eigenen — sie
    # arbeiten im Bereich ihres Inhabers und nutzen dessen Schlüssel (das ergibt
    # sich automatisch daraus, dass app_settings über workspace_owner_id
    # aufgelöst wird). Bestehende DBs: manuelles ALTER
    # (scripts/add_anthropic_key.sql).
    anthropic_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # KI-Lead-Suche: Standard-Modell + hartes Monatsbudget (EUR).
    ai_model: Mapped[str] = mapped_column(
        String(40), default="claude-sonnet-5", server_default="claude-sonnet-5", nullable=False)
    ai_monthly_budget_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("20"), server_default="20", nullable=False)
    # Automatische (schnelle, kostenlose) Website-Analyse nach dem Lead-Import.
    # Bestehende DBs: manuelles ALTER (scripts/add_auto_analyze.sql).
    auto_analyze_websites: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False)
