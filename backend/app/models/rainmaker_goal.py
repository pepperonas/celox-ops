import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.models.rainmaker_activity import RainmakerActivityType


class RainmakerGoal(Base):
    """A configurable acquisition goal/channel with a daily target.

    Examples: "Neukunden Telefon-Akquise" (call, 5/day), "LinkedIn anschreiben"
    (message, 5/day). Single-user — no owner FK.
    """

    __tablename__ = "rainmaker_goal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Activity type pre-selected when planning an action for this goal.
    suggested_type: Mapped[RainmakerActivityType] = mapped_column(
        Enum(RainmakerActivityType, native_enum=False, length=20), nullable=False
    )
    daily_target: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3", nullable=False
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Default goal set seeded on demand (POST /goals/seed). (name, type, daily_target).
DEFAULT_GOALS = [
    ("Neukunden Telefon-Akquise", RainmakerActivityType.call, 5),
    ("LinkedIn anschreiben", RainmakerActivityType.message, 5),
    ("Bestandskunde kontaktieren", RainmakerActivityType.follow_up, 2),
    ("E-Mail-Akquise", RainmakerActivityType.email, 5),
    ("Netzwerk / Empfehlung", RainmakerActivityType.note, 1),
]
