import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class OutreachChannel(str, enum.Enum):
    email = "email"
    linkedin = "linkedin"
    phone = "phone"


class OutreachCategory(str, enum.Enum):
    kaltakquise = "kaltakquise"
    followup = "followup"
    reaktivierung = "reaktivierung"
    empfehlung = "empfehlung"
    angebot_nachfassen = "angebot_nachfassen"
    security_upsell = "security_upsell"
    security_audit = "security_audit"
    ki_automatisierung = "ki_automatisierung"
    # Produktlinien mit eigener Argumentation (2026-07): DSMS/externer DSB,
    # Portal-Assessments, bcsbook. Werte bleiben ≤ 20 Zeichen — die Spalte ist
    # VARCHAR(20) (native_enum=False).
    datenschutz_dsms = "datenschutz_dsms"
    portal_assessment = "portal_assessment"
    bcsbook_zeit = "bcsbook_zeit"


class OutreachTemplate(OwnedMixin, Base):
    """Sofort einsatzbereite Akquise-Nachrichtenvorlage (E-Mail/LinkedIn/Telefon).
    Platzhalter-Syntax {{...}}; Telefon-Bodies gliedern sich über ##-Überschriften
    (Einstieg/Nutzenargument/Einwandbehandlung/Abschluss)."""

    __tablename__ = "outreach_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel: Mapped[OutreachChannel] = mapped_column(
        Enum(OutreachChannel, native_enum=False, length=10), nullable=False
    )
    category: Mapped[OutreachCategory] = mapped_column(
        Enum(OutreachCategory, native_enum=False, length=20), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)  # nur E-Mail
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)           # interne Hinweise
    # Reihenfolge JE KANAL (nicht je Rubrik): die Rubriken-Chips filtern nur eine
    # Sicht auf dieselbe Liste. Pro Filterkombination getrennte Positionen wären
    # verwirrend — eine Karte erschiene in „Alle Rubriken" und in ihrer Rubrik mit
    # zwei unabhängigen Plätzen. Gesetzt über `POST /templates/reorder`.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Reihenfolge INNERHALB der Favoriten — eine eigene Ordnung, weil die
    # Favoriten-Sektion kanalübergreifend ist. `sort_order` zählt je Kanal ab 0;
    # eine Telefonvorlage mit 0 und eine E-Mail mit 0 stünden dort also willkürlich
    # nebeneinander. NULL = noch nicht einsortiert; solche Favoriten hängen hinten,
    # damit ein neuer Stern die bestehende Anordnung nicht durchmischt.
    # Migration: scripts/add_outreach_favorite_order.sql.
    favorite_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Freie Einfärbung der Karte (wie Google Keep) — Schlüssel aus einer festen
    # Palette, nicht ein Farbwert: die konkreten Töne kommen aus den Theme-Tokens
    # im Frontend und dürfen sich ändern, ohne die Daten anzufassen.
    # NULL = neutral. Migration: scripts/add_outreach_card_style.sql.
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
