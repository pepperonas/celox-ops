"""Unit-Tests für den Google-Places-Nutzungszähler (DB-frei)."""
from app.services.places_usage import bump, calls_this_month, mask_key


def test_calls_this_month_same_period():
    assert calls_this_month("2026-07", 12, "2026-07") == 12


def test_calls_this_month_reset_on_new_month():
    assert calls_this_month("2026-06", 12, "2026-07") == 0
    assert calls_this_month(None, 5, "2026-07") == 0


def test_bump_increments_same_month():
    assert bump("2026-07", 3, "2026-07") == ("2026-07", 4)


def test_bump_resets_on_new_month():
    assert bump("2026-06", 99, "2026-07") == ("2026-07", 1)
    assert bump(None, 0, "2026-07") == ("2026-07", 1)


def test_bump_increment_counts_multiple_api_calls():
    # Google: 1 Text-Suche + N Place-Details = increment
    assert bump("2026-07", 10, "2026-07", increment=6) == ("2026-07", 16)
    assert bump("2026-06", 10, "2026-07", increment=6) == ("2026-07", 6)   # Monatswechsel
    assert bump("2026-07", 0, "2026-07", increment=0) == ("2026-07", 1)    # min. 1


def test_mask_key():
    assert mask_key("AIzaSyABCDEFG1234") == "••••1234"
    assert mask_key("xy") == "••••xy"
    assert mask_key("") is None
    assert mask_key(None) is None
