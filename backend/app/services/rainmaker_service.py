"""Rainmaker activation-engine helpers.

Central rule: a lead's "next action" is the planned activity with the earliest
due_date. An active lead (status not won/lost/dormant) WITHOUT a planned
activity is "rotting" and must be surfaced prominently.
"""
import logging
from datetime import date, datetime, time, timedelta, timezone

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
_reminder_sent_on: date | None = None

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


def display_streak(streak: RainmakerStreak, today: date) -> int:
    """The streak is 'alive' only if the quota was met today or yesterday;
    otherwise a full day was missed and it reads as 0."""
    if streak.last_quota_met_date and streak.last_quota_met_date >= today - timedelta(days=1):
        return streak.current_streak
    return 0


async def register_completion(db: AsyncSession, activity_type: RainmakerActivityType) -> None:
    """Award points for a completed activity and advance the daily-quota streak.

    Points per type (call=10, visit=20, email/message/follow_up=5); ×1.5 while on
    a streak of ≥7. The streak increments the first time today's quota is met."""
    settings = await get_or_create_settings(db)
    streak = await get_or_create_streak(db)
    today = date.today()

    base = ACTIVITY_POINTS.get(activity_type, 0)
    multiplier = 1.5 if display_streak(streak, today) >= 7 else 1.0
    streak.total_points += int(round(base * multiplier))

    # Recompute after this completion is persisted so it is counted.
    await db.flush()
    if await count_done_today(db) >= settings.daily_quota:
        if streak.last_quota_met_date == today:
            pass  # already counted today
        elif streak.last_quota_met_date == today - timedelta(days=1):
            streak.current_streak += 1
            streak.last_quota_met_date = today
        else:
            streak.current_streak = 1  # fresh start (first ever or after a gap)
            streak.last_quota_met_date = today
        streak.longest_streak = max(streak.longest_streak, streak.current_streak)


async def check_rainmaker_reminder(db: AsyncSession) -> bool:
    """Called hourly by run_cron. Sends one mail reminder per day at the
    configured hour if the daily quota is not yet met. Returns True if sent."""
    global _reminder_sent_on
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
    if _reminder_sent_on == today:
        return False

    done = await count_done_today(db)
    if done >= settings.daily_quota:
        return False

    to_email = app_settings.BUSINESS_EMAIL
    if not to_email or not app_settings.SMTP_HOST:
        return False

    streak = await get_or_create_streak(db)
    remaining = settings.daily_quota - done
    s = display_streak(streak, today)
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
    _reminder_sent_on = today
    logger.info("Rainmaker-Reminder gesendet (%d von %d offen)", remaining, settings.daily_quota)
    return True
