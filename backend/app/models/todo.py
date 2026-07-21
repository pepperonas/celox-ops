import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class TodoStatus(str, enum.Enum):
    offen = "offen"
    erledigt = "erledigt"


class TodoPriority(str, enum.Enum):
    niedrig = "niedrig"
    normal = "normal"
    hoch = "hoch"


class Todo(OwnedMixin, Base):
    """Manuelle To-dos — frei formulierbar, optional an einen Kunden ODER Lead
    gehängt (beides nullable = freies To-do ohne Bezug).

    Bewusst getrennt von den Rainmaker-Aktivitäten: die sind Akquise-Aktionen
    mit Punkten/Streak/Tagesquote und zwingen eine Folgeaktion ab. Ein To-do ist
    einfach eine Sache, die zu tun ist — es zahlt nicht in die Gamification ein
    und taucht nicht in der Heute-Queue auf.
    """

    __tablename__ = "todos"
    __table_args__ = (
        Index("idx_todos_status_due", "status", "due_date"),
        Index("idx_todos_customer_id", "customer_id"),
        Index("idx_todos_lead_id", "lead_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bezug: höchstens einer von beiden gesetzt (Router validiert owner-scoped).
    # SET NULL statt CASCADE — ein gelöschter Kunde soll das To-do nicht
    # mitreißen, es bleibt als freies To-do erhalten.
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rainmaker_leads.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[TodoPriority] = mapped_column(
        Enum(TodoPriority, native_enum=False, length=10),
        default=TodoPriority.normal,
        server_default="normal",
        nullable=False,
    )
    status: Mapped[TodoStatus] = mapped_column(
        Enum(TodoStatus, native_enum=False, length=10),
        default=TodoStatus.offen,
        server_default="offen",
        nullable=False,
    )
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Manuelle Reihenfolge innerhalb einer Gruppe (kleiner = weiter oben).
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
