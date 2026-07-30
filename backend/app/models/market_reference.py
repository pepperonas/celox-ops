"""Referenzkunde eines Herstellers — der eigentliche Lead-Kandidat des Marktradars.

**Warum eine Zwischenstufe und nicht direkt ein Lead.** Die 142 Katalogeinträge
zeigen auf rund 8.664 solche Firmen. Gingen die alle direkt in die Pipeline, wäre das
Board unbenutzbar und der Bestand nicht mehr zu übersehen. Hier liegen sie also als
Fundmaterial, aus dem gezielt ausgewählt wird — dasselbe Muster wie beim Katalog
selbst (`market_products` → Übergabe in die Pipeline).

**Die eine wichtige Modellentscheidung:** Eindeutig ist eine Firma **pro Hersteller**,
nicht global. Steht dieselbe Firma bei zwei Herstellern im Referenzverzeichnis, nutzt
sie zwei Systeme — das ist kein Duplikat, sondern der wertvollere Lead (zwei
Anknüpfungspunkte). Deshalb greift die Eindeutigkeit auf (owner, product, company).
Zusammengeführt wird erst beim Anlegen des Leads, dort über die vorhandene
`DedupIndex`.

Gespeichert werden nur **Firmenname und -Website** samt Quell-URL — keine
Personendaten.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


def norm_company(name: str | None) -> str:
    """Vergleichsschlüssel für einen Firmennamen. Rein.

    Bewusst grob (nur Buchstaben und Ziffern, klein): „Siemens AG", „SIEMENS AG" und
    „Siemens  AG" sind dieselbe Firma. Rechtsformen bleiben drin — „Muster GmbH" und
    „Muster AG" können verschiedene Gesellschaften derselben Gruppe sein, und
    zusammenzuführen, was verschieden ist, wäre der teurere Fehler.
    """
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


class MarketReference(OwnedMixin, Base):
    __tablename__ = "market_references"
    __table_args__ = (
        UniqueConstraint("owner_id", "product_id", "company_norm",
                         name="uq_market_references_owner_product_company"),
        Index("ix_market_references_owner_product", "owner_id", "product_id"),
        Index("ix_market_references_owner_status", "owner_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Wessen Software diese Firma einsetzt — daraus entsteht der Verkaufswinkel.
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("market_products.id", ondelete="CASCADE"),
        nullable=False, index=True)

    company: Mapped[str] = mapped_column(String(255), nullable=False)
    company_norm: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Herkunft: Ohne sie wäre nicht prüfbar, woher der Name kommt.
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    form: Mapped[str] = mapped_column(String(20), nullable=False)   # logowand|verlinkt|textliste

    # Bearbeitungsstand: neu → in_pipeline (Lead angelegt) oder verworfen.
    status: Mapped[str] = mapped_column(String(20), default="neu", nullable=False)
    rainmaker_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="SET NULL"), nullable=True)

    harvested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # --- Kontaktdaten (angereichert) ------------------------------------------
    # Gleiche Struktur wie bei den Herstellern: Werte plus Beleg je Feld. Die Website
    # stammt hier meist NICHT aus dem Verzeichnis, sondern aus einer Namensauflösung
    # über Google Places — `website_source` hält fest, woher: „verlinkt" (im
    # Verzeichnis verlinkt, sicher) oder „places" (aufgelöst, mit Namensprüfung).
    # Ohne diese Unterscheidung wäre nicht mehr erkennbar, welcher Wert wie belegt ist.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    decision_maker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contact_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
