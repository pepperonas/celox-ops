import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class LeadChatImport(OwnedMixin, Base):
    """Ein KI-Lauf „Lead aus Chat aktualisieren" — Vorschlag, Übernahme, Rücknahme.

    Bewusst eine eigene Tabelle (auto via `create_all`, **keine Migration**). Sie
    erfüllt drei Zwecke auf einmal:

    1. **Sicherheit:** `apply` bekommt nur die Auswahl-Keys, nicht die Werte. Die
       Werte kommen aus dem hier gespeicherten Vorschlag — ein manipulierter
       Request kann damit keine beliebigen Stammdaten schreiben.
    2. **Rücknahme:** `undo` kehrt genau diesen protokollierten Lauf um (Snapshot
       der vorherigen Werte + IDs der erzeugten Aktivitäten). Es nimmt keine
       fremden IDs an, kann also nicht zum Löschwerkzeug umgewidmet werden.
    3. **Nachvollziehbarkeit + Idempotenz:** identisches Material (`material_hash`)
       liefert denselben Vorschlag mit denselben Aktivitäts-Fingerprints.

    **Datenschutz (Entscheidung 2026-07-28):** Rohmaterial wird NICHT gespeichert
    — weder der eingefügte Chat-Text noch die Screenshots. Vom Material bleibt nur
    der Hash (für die Idempotenz). Chat-Screenshots enthalten regelmäßig Daten
    Dritter, und ein Lead ist kein Kunde: der DSGVO-Export und das Löschkonzept
    hängen am Kunden, gespeicherte Lead-Anhänge fielen durch dieses Raster. Die
    übernommenen Auszüge stehen ohnehin in den Aktivitäten — der Nachweis „woher
    kam die Information" ist damit erfüllt, ohne Rohdaten zu horten.
    """

    __tablename__ = "lead_chat_imports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Hash des Materials (Text + Bild-Digests) + Lead-Stand + Modell + Prompt-Version.
    material_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(10), nullable=False)
    model: Mapped[str] = mapped_column(String(40), nullable=False)
    images: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)

    # Der vollständige Vorschlag (Diff-Struktur), wie er dem Nutzer gezeigt wurde.
    proposal: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Was tatsächlich übernommen wurde + Snapshot davor (treibt die Rücknahme).
    applied: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    cost_eur: Mapped[float] = mapped_column(Numeric(10, 4), default=0, server_default="0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Wer übernommen hat — eine Mitarbeitendenrolle darf nur den EIGENEN Lauf
    # zurücknehmen (der Arbeitsbereich ist geteilt, die Verantwortung nicht).
    applied_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
