import enum
import uuid
from datetime import date as DateType, time as TimeType
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, Integer, Numeric, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class RainmakerReminderChannel(str, enum.Enum):
    email = "email"
    telegram = "telegram"
    push = "push"


class RainmakerDreamMode(str, enum.Enum):
    # Progress source: expected value of completed actions vs. real paid invoices.
    ev = "ev"
    invoices = "invoices"


class RainmakerSettings(OwnedMixin, Base):
    """Per-user single-row settings (get_or_create returns the owner's row via
    tenancy auto-scoping)."""

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
    # Streak-freeze days granted per month (buffer for vacation/sick days).
    freezes_per_month: Mapped[int] = mapped_column(
        Integer, default=2, server_default="2", nullable=False
    )

    # --- Traumziel (dream goal) — expected-value motivation engine ---
    # Preset key ("cayenne_turbo_e", …) or "custom"; name/price are denormalized
    # so a custom goal (or an edited preset price) survives preset changes.
    dream_goal_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dream_goal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dream_goal_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("165500"), server_default="165500", nullable=False
    )
    # Share of net revenue that goes into the dream fund (after taxes/costs).
    dream_savings_rate_pct: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30", nullable=False
    )
    # Acquisition assumptions driving the expected value of a single contact.
    dream_avg_deal_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("15000"), server_default="15000", nullable=False
    )
    dream_contacts_per_win: Mapped[int] = mapped_column(
        Integer, default=20, server_default="20", nullable=False
    )
    # Challenge start; set to "today" on first visit of the Traumziel view.
    dream_start_date: Mapped[DateType | None] = mapped_column(Date, nullable=True)
    dream_mode: Mapped[RainmakerDreamMode] = mapped_column(
        Enum(RainmakerDreamMode, native_enum=False, length=10),
        default=RainmakerDreamMode.ev,
        server_default="ev",
        nullable=False,
    )
