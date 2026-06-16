import enum
import uuid
from datetime import date as DateType, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.customer import Base


class RainmakerActivityType(str, enum.Enum):
    call = "call"
    email = "email"
    visit = "visit"
    message = "message"
    follow_up = "follow_up"
    note = "note"


class RainmakerActivityStatus(str, enum.Enum):
    planned = "planned"
    done = "done"
    skipped = "skipped"


class RainmakerOutcome(str, enum.Enum):
    reached = "reached"
    no_answer = "no_answer"
    positive = "positive"
    negative = "negative"
    meeting_set = "meeting_set"
    proposal_sent = "proposal_sent"
    not_interested = "not_interested"


# Points awarded per completed activity type (gamification, Phase 3).
ACTIVITY_POINTS = {
    RainmakerActivityType.call: 10,
    RainmakerActivityType.visit: 20,
    RainmakerActivityType.email: 5,
    RainmakerActivityType.message: 5,
    RainmakerActivityType.follow_up: 5,
    RainmakerActivityType.note: 0,
}


class RainmakerActivity(Base):
    __tablename__ = "rainmaker_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rainmaker_leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Optional acquisition goal this activity counts toward.
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rainmaker_goal.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[RainmakerActivityType] = mapped_column(
        Enum(RainmakerActivityType, native_enum=False, length=20), nullable=False
    )
    status: Mapped[RainmakerActivityStatus] = mapped_column(
        Enum(RainmakerActivityStatus, native_enum=False, length=10),
        default=RainmakerActivityStatus.planned,
        server_default="planned",
        nullable=False,
        index=True,
    )
    due_date: Mapped[DateType | None] = mapped_column(Date, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    outcome: Mapped[RainmakerOutcome | None] = mapped_column(
        Enum(RainmakerOutcome, native_enum=False, length=20), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lead: Mapped["RainmakerLead"] = relationship(  # noqa: F821
        "RainmakerLead", back_populates="activities"
    )
