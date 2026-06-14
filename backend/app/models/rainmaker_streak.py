import uuid
from datetime import date as DateType

from sqlalchemy import Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base


class RainmakerStreak(Base):
    """Single-row streak/points table (single-user — no owner FK)."""

    __tablename__ = "rainmaker_streak"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_quota_met_date: Mapped[DateType | None] = mapped_column(Date, nullable=True)
    total_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
