"""Marktradar: Lösungsbausteine — was sich über mehrere Produkte hinweg verkaufen lässt.

Ein Baustein (z. B. „Sprache → Dokumentation") ist eine Lösung, die auf viele
Katalogprodukte gleichzeitig passt. `catalog_ids` hält die Zuordnung als Liste
der Katalog-IDs; Reichweite, Ø-Score und Pipeline-Indikation werden **nicht**
gespeichert, sondern bei jeder Abfrage gegen die aktuell gefilterte Produktmenge
gerechnet — sonst zeigte die Karte eine Momentaufnahme, die dem Filter nicht folgt.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.customer import Base
from app.tenancy import OwnedMixin


class MarketBaustein(OwnedMixin, Base):
    __tablename__ = "market_bausteine"
    __table_args__ = (
        UniqueConstraint("owner_id", "nr", name="uq_market_bausteine_owner_nr"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nr: Mapped[int] = mapped_column(Integer, nullable=False)
    titel: Mapped[str] = mapped_column(String(255), nullable=False)
    was: Mapped[str | None] = mapped_column(Text, nullable=True)
    warum: Mapped[str | None] = mapped_column(Text, nullable=True)
    vorsicht: Mapped[str | None] = mapped_column(Text, nullable=True)
    aufwand: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
