import uuid
from datetime import date as DateType

from sqlalchemy import Date, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base


class RainmakerStreak(Base):
    """Single-row streak/points table (single-user — no owner FK).

    The streak counts working days (Mon–Fri) only; weekends never break it.
    Missed working days consume a monthly 'freeze' budget before the streak
    resets.
    """

    __tablename__ = "rainmaker_streak"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_quota_met_date: Mapped[DateType | None] = mapped_column(Date, nullable=True)
    total_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # Streak-freeze budget; replenished monthly to settings.freezes_per_month.
    freeze_remaining: Mapped[int] = mapped_column(Integer, default=2, server_default="2", nullable=False)
    # Year-month ("YYYY-MM") the current freeze budget belongs to.
    freeze_period: Mapped[str | None] = mapped_column(String(7), nullable=True)
