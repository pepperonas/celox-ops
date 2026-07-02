"""Rainmaker activation-engine helpers.

Central rule: a lead's "next action" is the planned activity with the earliest
due_date. An active lead (status not won/lost/dormant) WITHOUT a planned
activity is "rotting" and must be surfaced prominently.
"""
import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.rainmaker_activity import (
    ACTIVITY_POINTS,
    RainmakerActivity,
    RainmakerActivityStatus,
    RainmakerActivityType,
)
from app.models.rainmaker_lead import CLOSED_STATUSES, RainmakerLead
from app.models.rainmaker_settings import RainmakerSettings
from app.models.rainmaker_streak import RainmakerStreak
from app.schemas.rainmaker import RainmakerLeadResponse
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

# In-memory dedupe so the hourly cron sends at most one reminder per day
# (mirrors the dashboard _stats_cache pattern; reset on process restart).
# Per-user dedupe: {user_id: date} — one reminder per user per day.
_reminder_sent_on: dict = {}

# Sort weight for lead priority (high first).
_PRIORITY_WEIGHT = {"high": 0, "medium": 1, "low": 2}


def planned_activities(lead: RainmakerLead) -> list[RainmakerActivity]:
    return [a for a in lead.activities if a.status == RainmakerActivityStatus.planned]


def next_planned_activity(lead: RainmakerLead) -> RainmakerActivity | None:
    """Earliest planned activity (by due_date, then creation order). None if none."""
    planned = planned_activities(lead)
    if not planned:
        return None
    return min(planned, key=lambda a: (a.due_date or date.max, a.created_at))


def is_rotting(lead: RainmakerLead) -> bool:
    """Active lead without any planned next step."""
    if lead.status in CLOSED_STATUSES:
        return False
    return not planned_activities(lead)


def lead_response(lead: RainmakerLead) -> RainmakerLeadResponse:
    """Build a lead response enriched with the computed next-action fields."""
    resp = RainmakerLeadResponse.model_validate(lead)
    nxt = next_planned_activity(lead)
    if nxt:
        resp.next_action_type = nxt.type
        resp.next_action_due = nxt.due_date
        resp.next_action_id = nxt.id
    resp.needs_next_action = is_rotting(lead)
    return resp


def priority_weight(lead: RainmakerLead) -> int:
    return _PRIORITY_WEIGHT.get(
        lead.priority.value if hasattr(lead.priority, "value") else str(lead.priority), 1
    )


# --------------------------------------------------------------------------- #
#  Gamification: settings + streak singletons, pensum, points
# --------------------------------------------------------------------------- #
async def get_or_create_settings(db: AsyncSession) -> RainmakerSettings:
    row = (await db.execute(select(RainmakerSettings).limit(1))).scalar_one_or_none()
    if row is None:
        row = RainmakerSettings()
        db.add(row)
        await db.flush()
    return row


async def get_or_create_streak(db: AsyncSession) -> RainmakerStreak:
    row = (await db.execute(select(RainmakerStreak).limit(1))).scalar_one_or_none()
    if row is None:
        row = RainmakerStreak()
        db.add(row)
        await db.flush()
    return row


async def count_done_today(db: AsyncSession) -> int:
    """Activities completed today (UTC day)."""
    start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    result = await db.execute(
        select(func.count())
        .select_from(RainmakerActivity)
        .where(
            RainmakerActivity.status == RainmakerActivityStatus.done,
            RainmakerActivity.completed_at >= start,
        )
    )
    return int(result.scalar_one())


def is_working_day(d: date) -> bool:
    """Mon–Fri count toward the streak; weekends are neutral."""
    return d.weekday() < 5


def missed_working_days(last_met: date | None, today: date) -> int:
    """Working days strictly between last_met and today (today still in progress,
    so excluded). Weekends don't count as missed."""
    if last_met is None:
        return 0
    n = 0
    d = last_met + timedelta(days=1)
    while d < today:
        if is_working_day(d):
            n += 1
        d += timedelta(days=1)
    return n


def display_streak(streak: RainmakerStreak, today: date) -> int:
    """Working-day streak with freeze buffer: alive if the working days missed
    since the last quota-met day don't exceed the remaining freeze budget."""
    if not streak.last_quota_met_date or streak.current_streak <= 0:
        return 0
    if missed_working_days(streak.last_quota_met_date, today) <= streak.freeze_remaining:
        return streak.current_streak
    return 0


def _period_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


async def _ensure_monthly_freezes(
    db: AsyncSession, streak: RainmakerStreak, settings: RainmakerSettings
) -> None:
    """Replenish the freeze budget at the start of each month."""
    key = _period_key(date.today())
    if streak.freeze_period != key:
        streak.freeze_remaining = settings.freezes_per_month
        streak.freeze_period = key


async def get_streak_display(db: AsyncSession) -> tuple[RainmakerStreak, int]:
    """Streak row (freezes replenished) + its current display value."""
    settings = await get_or_create_settings(db)
    streak = await get_or_create_streak(db)
    await _ensure_monthly_freezes(db, streak, settings)
    return streak, display_streak(streak, date.today())


async def register_completion(db: AsyncSession, activity_type: RainmakerActivityType) -> None:
    """Award points for a completed activity and advance the working-day streak.

    Points per type (call=10, visit=20, email/message/follow_up=5); ×1.5 while on
    a streak of ≥7. The streak increments the first time today's quota is met on a
    working day; missed working days consume freezes before the streak resets."""
    settings = await get_or_create_settings(db)
    streak = await get_or_create_streak(db)
    today = date.today()
    await _ensure_monthly_freezes(db, streak, settings)

    base = ACTIVITY_POINTS.get(activity_type, 0)
    multiplier = 1.5 if display_streak(streak, today) >= 7 else 1.0
    streak.total_points += int(round(base * multiplier))

    # Recompute after this completion is persisted so it is counted.
    await db.flush()
    if await count_done_today(db) >= settings.daily_quota:
        # Weekends are bonus (points only) — the streak tracks working days.
        if is_working_day(today) and streak.last_quota_met_date != today:
            missed = missed_working_days(streak.last_quota_met_date, today)
            if missed <= streak.freeze_remaining:
                streak.freeze_remaining -= missed  # spend freezes to bridge the gap
                streak.current_streak += 1
            else:
                streak.current_streak = 1  # too many missed working days → reset
            streak.last_quota_met_date = today
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)


# --------------------------------------------------------------------------- #
#  Traumziel (dream goal): expected-value engine
#
#  The motivational core: every completed acquisition action carries a
#  statistical value toward the dream, even when the answer is "no". With the
#  default assumptions (Ø deal 15k €, 20 contacts per win, 30 % savings rate)
#  one call is worth 15000 × 0.30 / 20 = 225 € toward the goal.
# --------------------------------------------------------------------------- #
# Relative weight of each activity type against one "contact unit" (= a call).
DREAM_EV_WEIGHTS: dict[RainmakerActivityType, float] = {
    RainmakerActivityType.call: 1.0,
    RainmakerActivityType.visit: 2.5,
    RainmakerActivityType.email: 0.4,
    RainmakerActivityType.message: 0.4,
    RainmakerActivityType.follow_up: 0.8,
    RainmakerActivityType.note: 0.0,
}


def dream_ev_per_contact(
    avg_deal_value: Decimal | int | float,
    savings_rate_pct: int,
    contacts_per_win: int,
) -> Decimal:
    """Expected € toward the dream per weight-1.0 contact (one call)."""
    if contacts_per_win <= 0 or savings_rate_pct <= 0:
        return Decimal("0.00")
    value = (
        Decimal(str(avg_deal_value)) * Decimal(savings_rate_pct) / Decimal(100)
    ) / Decimal(contacts_per_win)
    return value.quantize(Decimal("0.01"))


def dream_activities_ev(
    counts_by_type: dict[RainmakerActivityType, int], ev_per_contact: Decimal
) -> Decimal:
    """Total expected value of a set of completed activities."""
    total = Decimal("0")
    for activity_type, count in counts_by_type.items():
        weight = DREAM_EV_WEIGHTS.get(activity_type, 0.0)
        total += ev_per_contact * Decimal(str(weight)) * count
    return total.quantize(Decimal("0.01"))


def dream_projected_date(
    remaining: Decimal, pace_per_day: Decimal, today: date
) -> date | None:
    """Finish date at the current pace. None while there is no pace yet or the
    projection is beyond any horizon a human plans with (> 50 years)."""
    if remaining <= 0:
        return today
    if pace_per_day <= 0:
        return None
    days = int(remaining / pace_per_day) + 1
    if days > 18250:
        return None
    return today + timedelta(days=days)


async def check_rainmaker_reminder(db: AsyncSession, user=None) -> bool:
    """Called hourly by run_cron, once per active user (owner ContextVar set by the
    caller). Sends one mail reminder per user per day at the configured hour if the
    daily quota is not yet met. Returns True if sent."""
    settings = await get_or_create_settings(db)
    if not settings.reminder_enabled:
        return False
    # Phase 4 supports the email channel only.
    channel = settings.reminder_channel.value if hasattr(settings.reminder_channel, "value") else str(settings.reminder_channel)
    if channel != "email":
        return False

    now = datetime.now()
    if now.hour != settings.reminder_time.hour:
        return False

    today = date.today()
    dedupe_key = getattr(user, "id", None)
    if _reminder_sent_on.get(dedupe_key) == today:
        return False

    done = await count_done_today(db)
    if done >= settings.daily_quota:
        return False

    # Send to the user's own email; fall back to the global business address.
    to_email = getattr(user, "email", None) or app_settings.BUSINESS_EMAIL
    if not to_email or not app_settings.SMTP_HOST:
        return False

    _streak, s = await get_streak_display(db)
    remaining = settings.daily_quota - done
    streak_line = f"Streak: {s} Tag{'e' if s != 1 else ''} 🔥<br>" if s else ""
    body_html = (
        f"Du hast heute noch <strong>{remaining} von {settings.daily_quota}</strong> "
        f"Akquise-Aktionen offen.<br>{streak_line}<br>"
        f"→ Rainmaker öffnen und dranbleiben."
    )
    await send_email(
        to_email=to_email,
        subject=f"Rainmaker: noch {remaining} offen heute",
        body_html=body_html,
    )
    _reminder_sent_on[dedupe_key] = today
    logger.info("Rainmaker-Reminder gesendet (%d von %d offen)", remaining, settings.daily_quota)
    return True
