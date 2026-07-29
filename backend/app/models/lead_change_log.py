"""Änderungsprotokoll für Leads — mit Vorher-Werten, damit man zurück kann.

Warum nicht eine Freigabe-Warteschlange? Ein Verkäufer zieht Karten dutzende Male
am Tag durch die Phasen. Müsste jede Änderung erst freigegeben werden, sähe er
seine eigene Arbeit nicht (das Board würde ihn belügen) und der Inhaber wäre der
Flaschenhals. Stattdessen: Änderungen wirken sofort, sind aber protokolliert und
per Klick zurücknehmbar — dieselbe Sicherheit, ohne die Arbeit zu blockieren.

Warum nicht das bestehende `audit_log`? Das protokolliert Requests (Methode, Pfad,
Status) für die Nachvollziehbarkeit. Zum Zurücknehmen braucht man die **Werte**
vorher und nachher, und zwar feldweise. Das ist ein anderer Zweck und eine andere
Lebensdauer.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.customer import Base
from app.tenancy import OwnedMixin


class LeadChangeLog(OwnedMixin, Base):
    """Eine Zeile pro Änderungs-Satz (nicht pro Feld) — ein Speichern im Formular
    ist ein Vorgang und wird als einer zurückgenommen."""

    __tablename__ = "lead_change_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Lead bleibt beim endgültigen Löschen nicht erhalten → SET NULL statt CASCADE:
    # das Protokoll soll überleben, dass der Lead entfernt wurde.
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="SET NULL"), nullable=True,
        index=True,
    )
    # Für die Anzeige, wenn der Lead weg ist (SET NULL oben).
    lead_company: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_username: Mapped[str] = mapped_column(String(150), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Was passiert ist: "update" | "delete" | "restore" | "create"
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    # {feld: {"old": …, "new": …}} — JSON-serialisierbare Werte (Decimal/date als
    # String). Bei "delete"/"create" leer: dort ist der Vorgang selbst die Info.
    changes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Gesetzt, sobald der Inhaber diesen Vorgang zurückgenommen hat — einmalig,
    # damit ein zweiter Klick nicht erneut „zurücknimmt" und dabei neuere
    # Änderungen überschreibt.
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
