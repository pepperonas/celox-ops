"""Unit tests for the B5 sargable month-range helper (routers/dashboard._month_bounds).
Pure logic, no DB. The half-open [start, end) is what makes date filters index-usable."""
from datetime import date

from app.routers.dashboard import _month_bounds


def test_january():
    assert _month_bounds(2026, 1) == (date(2026, 1, 1), date(2026, 2, 1))


def test_mid_year():
    assert _month_bounds(2026, 7) == (date(2026, 7, 1), date(2026, 8, 1))


def test_december_rolls_into_next_year():
    assert _month_bounds(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))


def test_february_leap_and_non_leap_boundaries_are_month_starts():
    # end is always the 1st of the next month, regardless of month length
    assert _month_bounds(2024, 2) == (date(2024, 2, 1), date(2024, 3, 1))
    assert _month_bounds(2025, 2) == (date(2025, 2, 1), date(2025, 3, 1))


def test_all_months_half_open_and_ordered():
    for m in range(1, 13):
        start, end = _month_bounds(2026, m)
        assert start.day == 1 and end.day == 1
        assert end > start
        # start is in the requested month; end is the following month's first day
        assert start.month == m
        expected_end = date(2026 + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
        assert end == expected_end
