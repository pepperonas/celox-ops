"""Gecachter KI-Vorschlag für Kunden-To-dos.

Zweck ist Sparsamkeit, nicht Persistenz: solange sich an den Kundendaten nichts
geändert hat, liefert ein erneuter Klick denselben Vorschlag **ohne** KI-Aufruf
(0 €). Der Schlüssel ist ein Inhalts-Hash über den erzeugten Kontext plus Modell
und Prompt-Version — jede relevante Änderung entwertet ihn automatisch.

Neue Tabelle ⇒ `create_all` erzeugt sie, keine Migration (Repo-Konvention: nur
neue *Spalten* brauchen ein `ALTER`).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class CustomerTodoSuggestion(OwnedMixin, Base):
    __tablename__ = "customer_todo_suggestions"
    __table_args__ = (
        # Ein gültiger Vorschlag je Kunde; der Hash entscheidet, ob er noch passt.
        Index("uq_customer_todo_suggestion", "owner_id", "customer_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    # sha256 über Kontext + Modell + Prompt-Version.
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Das geprüfte Ergebnis als JSON-Text (Vorschläge + „nicht übernommen").
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
