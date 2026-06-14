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
    next_planned_activity,
)

TODAY = date(2026, 6, 14)


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
#  Streak display (alive vs. broken)
# --------------------------------------------------------------------------- #
def test_streak_alive_when_met_today():
    s = RainmakerStreak(current_streak=4, last_quota_met_date=TODAY)
    assert display_streak(s, TODAY) == 4


def test_streak_alive_when_met_yesterday():
    s = RainmakerStreak(current_streak=4, last_quota_met_date=TODAY - timedelta(days=1))
    assert display_streak(s, TODAY) == 4


def test_streak_broken_when_day_missed():
    s = RainmakerStreak(current_streak=9, last_quota_met_date=TODAY - timedelta(days=2))
    assert display_streak(s, TODAY) == 0


def test_streak_zero_when_never_met():
    s = RainmakerStreak(current_streak=0, last_quota_met_date=None)
    assert display_streak(s, TODAY) == 0


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
