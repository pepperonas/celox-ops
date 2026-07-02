"""Unit tests for the Traumziel expected-value engine (rainmaker_service).
Pure logic, no DB. The motivational core: every completed action carries a
statistical value toward the dream goal — even a "no" on the phone.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.models.rainmaker_activity import RainmakerActivityType
from app.services.rainmaker_service import (
    DREAM_EV_WEIGHTS,
    dream_activities_ev,
    dream_ev_per_contact,
    dream_projected_date,
)


# --------------------------------------------------------------------------- #
#  dream_ev_per_contact
# --------------------------------------------------------------------------- #
def test_default_assumptions_make_a_call_worth_225_euro():
    # Ø deal 15k € · 30 % savings rate · 20 contacts per win → 225 €/call.
    assert dream_ev_per_contact(15000, 30, 20) == Decimal("225.00")


def test_ev_scales_linearly_with_deal_value_and_rate():
    assert dream_ev_per_contact(30000, 30, 20) == Decimal("450.00")
    assert dream_ev_per_contact(15000, 60, 20) == Decimal("450.00")
    assert dream_ev_per_contact(15000, 30, 10) == Decimal("450.00")


def test_ev_guards_against_zero_or_negative_inputs():
    assert dream_ev_per_contact(15000, 30, 0) == Decimal("0.00")
    assert dream_ev_per_contact(15000, 0, 20) == Decimal("0.00")
    assert dream_ev_per_contact(15000, -5, 20) == Decimal("0.00")


def test_ev_is_quantized_to_cents():
    # 10000 × 0.33 / 7 = 471.428… → 471.43
    assert dream_ev_per_contact(10000, 33, 7) == Decimal("471.43")


# --------------------------------------------------------------------------- #
#  dream_activities_ev
# --------------------------------------------------------------------------- #
def test_activity_weights_shape():
    # Calls are the unit; visits weigh more, passive types less, notes nothing.
    assert DREAM_EV_WEIGHTS[RainmakerActivityType.call] == 1.0
    assert DREAM_EV_WEIGHTS[RainmakerActivityType.visit] > 1.0
    assert DREAM_EV_WEIGHTS[RainmakerActivityType.email] < 1.0
    assert DREAM_EV_WEIGHTS[RainmakerActivityType.note] == 0.0
    assert set(DREAM_EV_WEIGHTS) == set(RainmakerActivityType)


def test_activities_ev_sums_weighted_counts():
    ev = Decimal("225.00")
    counts = {
        RainmakerActivityType.call: 4,       # 4 × 1.0 × 225 = 900
        RainmakerActivityType.visit: 1,      # 1 × 2.5 × 225 = 562.50
        RainmakerActivityType.email: 5,      # 5 × 0.4 × 225 = 450
        RainmakerActivityType.note: 10,      # 0
    }
    assert dream_activities_ev(counts, ev) == Decimal("1912.50")


def test_activities_ev_empty_is_zero():
    assert dream_activities_ev({}, Decimal("225.00")) == Decimal("0.00")


def test_a_no_still_counts():
    # The point of the whole feature: one completed call — regardless of the
    # outcome — moves the bar by the full expected value.
    one_call = {RainmakerActivityType.call: 1}
    assert dream_activities_ev(one_call, Decimal("225.00")) == Decimal("225.00")


# --------------------------------------------------------------------------- #
#  dream_projected_date
# --------------------------------------------------------------------------- #
def test_projection_at_steady_pace():
    today = date(2026, 7, 1)
    # 10 000 € remaining at 100 €/day → 101 days out.
    assert dream_projected_date(Decimal("10000"), Decimal("100"), today) == today + timedelta(days=101)


def test_projection_reached_goal_is_today():
    today = date(2026, 7, 1)
    assert dream_projected_date(Decimal("0"), Decimal("100"), today) == today
    assert dream_projected_date(Decimal("-50"), Decimal("0"), today) == today


def test_projection_without_pace_is_none():
    assert dream_projected_date(Decimal("10000"), Decimal("0"), date(2026, 7, 1)) is None


def test_projection_beyond_50_years_is_none():
    # 200 000 € at 1 ct/day is a fantasy, not a date.
    assert dream_projected_date(Decimal("200000"), Decimal("0.01"), date(2026, 7, 1)) is None
