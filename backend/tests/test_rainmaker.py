"""Unit tests for the Rainmaker activation engine — pure logic, no DB required.
Run via: cd backend && pytest -v tests/test_rainmaker.py
"""
import os
from datetime import date, datetime, timedelta, timezone

# Set required env BEFORE importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters-long")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

from app.models.rainmaker_activity import (  # noqa: E402
    ACTIVITY_POINTS,
    RainmakerActivity,
    RainmakerActivityStatus,
    RainmakerActivityType,
)
from app.models.rainmaker_lead import RainmakerLead, RainmakerLeadStatus  # noqa: E402
from app.models.rainmaker_streak import RainmakerStreak  # noqa: E402
from app.services.rainmaker_service import (  # noqa: E402
    display_streak,
    is_rotting,
    is_working_day,
    missed_working_days,
    next_planned_activity,
)

TODAY = date(2026, 6, 14)
# Anchor a known Monday so weekday-dependent assertions are calendar-safe.
MONDAY = date(2026, 6, 15) - timedelta(days=date(2026, 6, 15).weekday())
TUESDAY = MONDAY + timedelta(days=1)
WEDNESDAY = MONDAY + timedelta(days=2)
THURSDAY = MONDAY + timedelta(days=3)
PREV_FRIDAY = MONDAY - timedelta(days=3)


def _activity(status, due_date, created_at, type_=RainmakerActivityType.call):
    return RainmakerActivity(
        type=type_, status=status, due_date=due_date, created_at=created_at
    )


def _lead(status, activities):
    return RainmakerLead(company="X", status=status, activities=activities)


# --------------------------------------------------------------------------- #
#  Verrottende Leads (anti-stalling)
# --------------------------------------------------------------------------- #
def test_active_lead_without_planned_is_rotting():
    lead = _lead(RainmakerLeadStatus.new, [])
    assert is_rotting(lead) is True


def test_active_lead_with_planned_is_not_rotting():
    a = _activity(RainmakerActivityStatus.planned, TODAY, datetime.now(timezone.utc))
    lead = _lead(RainmakerLeadStatus.contacted, [a])
    assert is_rotting(lead) is False


def test_closed_lead_is_never_rotting():
    for st in (RainmakerLeadStatus.won, RainmakerLeadStatus.lost, RainmakerLeadStatus.dormant):
        assert is_rotting(_lead(st, [])) is False


def test_lead_with_only_done_activity_is_rotting():
    done = _activity(RainmakerActivityStatus.done, TODAY, datetime.now(timezone.utc))
    assert is_rotting(_lead(RainmakerLeadStatus.contacted, [done])) is True


# --------------------------------------------------------------------------- #
#  Next action selection
# --------------------------------------------------------------------------- #
def test_next_action_picks_earliest_due_planned():
    base = datetime.now(timezone.utc)
    late = _activity(RainmakerActivityStatus.planned, TODAY + timedelta(days=5), base)
    early = _activity(RainmakerActivityStatus.planned, TODAY + timedelta(days=1), base + timedelta(seconds=1))
    done = _activity(RainmakerActivityStatus.done, TODAY - timedelta(days=1), base)
    lead = _lead(RainmakerLeadStatus.contacted, [late, early, done])
    nxt = next_planned_activity(lead)
    assert nxt is early


def test_next_action_none_when_no_planned():
    done = _activity(RainmakerActivityStatus.done, TODAY, datetime.now(timezone.utc))
    assert next_planned_activity(_lead(RainmakerLeadStatus.new, [done])) is None


# --------------------------------------------------------------------------- #
#  Working days
# --------------------------------------------------------------------------- #
def test_is_working_day():
    assert is_working_day(MONDAY) is True
    assert is_working_day(MONDAY + timedelta(days=5)) is False  # Saturday
    assert is_working_day(MONDAY + timedelta(days=6)) is False  # Sunday


def test_missed_working_days_skips_weekend():
    # Fri → Mon: Sat+Sun are not working days → none missed
    assert missed_working_days(PREV_FRIDAY, MONDAY) == 0
    # Mon → Wed: Tue missed
    assert missed_working_days(MONDAY, WEDNESDAY) == 1
    # Mon → Thu: Tue+Wed missed
    assert missed_working_days(MONDAY, THURSDAY) == 2
    assert missed_working_days(None, MONDAY) == 0


# --------------------------------------------------------------------------- #
#  Streak display (working-day + freeze aware)
# --------------------------------------------------------------------------- #
def test_streak_alive_same_day():
    s = RainmakerStreak(current_streak=4, last_quota_met_date=MONDAY, freeze_remaining=2)
    assert display_streak(s, MONDAY) == 4


def test_streak_survives_weekend_without_freeze():
    s = RainmakerStreak(current_streak=8, last_quota_met_date=PREV_FRIDAY, freeze_remaining=0)
    assert display_streak(s, MONDAY) == 8


def test_streak_alive_when_missed_day_covered_by_freeze():
    s = RainmakerStreak(current_streak=5, last_quota_met_date=MONDAY, freeze_remaining=1)
    assert display_streak(s, WEDNESDAY) == 5  # Tue missed, 1 freeze covers it


def test_streak_broken_when_missed_day_exceeds_freeze():
    s = RainmakerStreak(current_streak=5, last_quota_met_date=MONDAY, freeze_remaining=0)
    assert display_streak(s, WEDNESDAY) == 0  # Tue missed, no freeze


def test_streak_broken_when_two_missed_exceed_one_freeze():
    s = RainmakerStreak(current_streak=9, last_quota_met_date=MONDAY, freeze_remaining=1)
    assert display_streak(s, THURSDAY) == 0  # Tue+Wed missed, only 1 freeze


def test_streak_zero_when_never_met():
    s = RainmakerStreak(current_streak=0, last_quota_met_date=None, freeze_remaining=2)
    assert display_streak(s, MONDAY) == 0


# --------------------------------------------------------------------------- #
#  Points table
# --------------------------------------------------------------------------- #
def test_activity_points_table():
    assert ACTIVITY_POINTS[RainmakerActivityType.call] == 10
    assert ACTIVITY_POINTS[RainmakerActivityType.visit] == 20
    assert ACTIVITY_POINTS[RainmakerActivityType.email] == 5
    assert ACTIVITY_POINTS[RainmakerActivityType.message] == 5
    assert ACTIVITY_POINTS[RainmakerActivityType.follow_up] == 5
    assert ACTIVITY_POINTS[RainmakerActivityType.note] == 0
