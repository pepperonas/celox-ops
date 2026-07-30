"""Marktradar: importierter Softwarekatalog + eigener Bearbeitungsstand.

Die Rechercheseite (Repo `pepperonas/business-opportunities`, privat) pflegt den
Katalog: DACH-Softwareprodukte mit öffentlichem Referenzverzeichnis, jeweils mit
Prozessen, täglichen Nutzern, manuellen Tätigkeiten, KI-Hebeln und einem dort
berechneten Opportunity Score. Dieses Modul **spiegelt** diesen Stand — es
berechnet ihn nicht neu. Der Score bleibt dort die einzige Wahrheit; hier eine
zweite Implementierung zu halten, würde zwangsläufig auseinanderlaufen.

Was ops beisteuert, sind die Arbeitsfelder: `status`, `ops_note` und die
Verknüpfung zum Rainmaker-Lead. Sie überleben jeden Re-Import (siehe
`services/market_import.py`) — sonst wäre eine Katalog-Aktualisierung ein
Rücksetzen der eigenen Arbeit.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.customer import Base
from app.tenancy import OwnedMixin


class MarketStatus(str, enum.Enum):
    """Bearbeitungsstand eines Katalogeintrags — nicht zu verwechseln mit dem
    Lead-Status im Rainmaker. Hier geht es nur darum, was ich mit dem *Eintrag*
    schon gemacht habe."""

    neu = "neu"
    gesichtet = "gesichtet"
    vorgemerkt = "vorgemerkt"
    in_pipeline = "in_pipeline"
    verworfen = "verworfen"


# Status, ab dem der Eintrag als abgearbeitet gilt (zählt nicht mehr in "offen").
CLOSED_STATUSES = {MarketStatus.in_pipeline, MarketStatus.verworfen}


class MarketProduct(OwnedMixin, Base):
    __tablename__ = "market_products"
    __table_args__ = (
        # Ein Katalogeintrag existiert pro Mandant genau einmal — darüber läuft
        # der idempotente Re-Import (Upsert statt Dublette).
        UniqueConstraint("owner_id", "catalog_id", name="uq_market_products_owner_catalog"),
        Index("ix_market_products_owner_score", "owner_id", "score"),
        Index("ix_market_products_owner_status", "owner_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Katalog-Identität ────────────────────────────────────────────────────
    catalog_id: Mapped[str] = mapped_column(String(80), nullable=False)
    produkt: Mapped[str] = mapped_column(String(255), nullable=False)
    hersteller: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    konzern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    konzern_slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    kategorie: Mapped[str] = mapped_column(String(160), nullable=False, index=True)

    # ── Referenzverzeichnis (der eigentliche Grund für den Katalog) ──────────
    ref_url: Mapped[str] = mapped_column(Text, nullable=False)
    ref_status: Mapped[str] = mapped_column(String(20), nullable=False)   # oeffentlich|teilweise|auf_anfrage|unklar
    url_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    url_geprueft: Mapped[str | None] = mapped_column(String(40), nullable=True)
    refs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kunden: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Fachliche Beschreibung ───────────────────────────────────────────────
    zielgruppe: Mapped[str | None] = mapped_column(Text, nullable=True)
    branchen: Mapped[list | None] = mapped_column(JSON, nullable=True)
    prozesse: Mapped[list | None] = mapped_column(JSON, nullable=True)
    nutzer: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pains: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ki: Mapped[list | None] = mapped_column(JSON, nullable=True)
    nutzen: Mapped[str | None] = mapped_column(Text, nullable=True)
    integration: Mapped[str | None] = mapped_column(Text, nullable=True)
    int_level: Mapped[str] = mapped_column(String(10), default="mittel", nullable=False)  # leicht|mittel|schwer
    ease: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    notiz: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Bewertung (kommt fertig aus dem Katalog) ─────────────────────────────
    lead: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    business: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prio: Mapped[str] = mapped_column(String(1), default="C", nullable=False)
    dach: Mapped[str | None] = mapped_column(String(20), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    breakdown: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Abgeleitete Signale ──────────────────────────────────────────────────
    marketplace: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mp_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reg: Mapped[list | None] = mapped_column(JSON, nullable=True)
    self_compete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Arbeitsstand in ops (überlebt den Re-Import) ─────────────────────────
    status: Mapped[MarketStatus] = mapped_column(
        Enum(MarketStatus, name="marketstatus"), default=MarketStatus.neu, nullable=False
    )
    ops_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rainmaker_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Herkunft ─────────────────────────────────────────────────────────────
    catalog_stand: Mapped[str | None] = mapped_column(String(20), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
