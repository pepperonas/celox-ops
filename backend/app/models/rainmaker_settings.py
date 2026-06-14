import enum
import uuid
from datetime import time as TimeType

from sqlalchemy import Boolean, Enum, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base


class RainmakerReminderChannel(str, enum.Enum):
    email = "email"
    telegram = "telegram"
    push = "push"


class RainmakerSettings(Base):
    """Single-row settings table (celox ops is single-user — no owner FK)."""

    __tablename__ = "rainmaker_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    daily_quota: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    reminder_time: Mapped[TimeType] = mapped_column(
        Time, default=TimeType(18, 0), nullable=False
    )
    reminder_channel: Mapped[RainmakerReminderChannel] = mapped_column(
        Enum(RainmakerReminderChannel, native_enum=False, length=10),
        default=RainmakerReminderChannel.email,
        server_default="email",
        nullable=False,
    )
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
