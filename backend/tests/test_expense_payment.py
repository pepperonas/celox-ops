"""Zahlungsstand und Ausgaben-Beschreibungs-Taxonomie."""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal

import pytest

from app.data.expense_descriptions import (
    EXPENSE_DESCRIPTION_CATEGORY,
    EXPENSE_DESCRIPTIONS,
    all_descriptions,
    category_for_description,
)
from app.schemas.expense import ExpenseCreate, ExpensePaymentUpdate
from app.services.expense_payment import (
    cash_date,
    counts_in_tax_year,
    normalize_payment,
)
from app.services.taxonomy import TAXONOMIES, merge_suggestions


# --------------------------------------------------------------------------- #
# normalize_payment
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "paid,paid_at,expense_date,expected",
    [
        (False, date(2026, 1, 5), date(2026, 1, 1), (False, None)),
        (False, None, date(2026, 1, 1), (False, None)),
        (False, date(2026, 6, 1), None, (False, None)),
        (True, None, date(2026, 3, 15), (True, date(2026, 3, 15))),
        (True, date(2026, 4, 1), date(2026, 3, 1), (True, date(2026, 4, 1))),
        (True, date(2026, 4, 1), None, (True, date(2026, 4, 1))),
        (True, None, None, (True, None)),
        (True, date(2025, 12, 31), date(2026, 1, 1), (True, date(2025, 12, 31))),
    ],
)
def test_normalize_payment_matrix(paid, paid_at, expense_date, expected):
    assert normalize_payment(
        paid=paid, paid_at=paid_at, expense_date=expense_date,
    ) == expected


def test_normalize_payment_unpaid_always_clears_even_with_future_paid_at():
    assert normalize_payment(
        paid=False, paid_at=date(2099, 1, 1), expense_date=date(2026, 1, 1),
    ) == (False, None)


# --------------------------------------------------------------------------- #
# cash_date / tax year (EÜR)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "paid,paid_at,expense_date,expected",
    [
        (False, date(2026, 5, 1), date(2026, 1, 1), None),
        (False, None, date(2026, 1, 1), None),
        (True, date(2026, 5, 10), date(2026, 1, 1), date(2026, 5, 10)),
        (True, None, date(2026, 1, 15), date(2026, 1, 15)),
        (True, None, None, None),
    ],
)
def test_cash_date(paid, paid_at, expense_date, expected):
    assert cash_date(paid=paid, paid_at=paid_at, expense_date=expense_date) == expected


@pytest.mark.parametrize(
    "paid,paid_at,expense_date,year,expected",
    [
        # Bezahlt im Jahr → zählt
        (True, date(2026, 3, 1), date(2026, 1, 1), 2026, True),
        # Bezahlt, paid_at im Vorjahr, Buchung 2026 → Vorjahr (Cash)
        (True, date(2025, 12, 28), date(2026, 1, 2), 2026, False),
        (True, date(2025, 12, 28), date(2026, 1, 2), 2025, True),
        # Ohne paid_at → Buchungsdatum
        (True, None, date(2026, 7, 1), 2026, True),
        (True, None, date(2026, 7, 1), 2025, False),
        # Offen zählt nie
        (False, date(2026, 3, 1), date(2026, 1, 1), 2026, False),
        (False, None, date(2026, 1, 1), 2026, False),
        # Silvester / Neujahr
        (True, date(2026, 12, 31), date(2026, 12, 1), 2026, True),
        (True, date(2027, 1, 1), date(2026, 12, 31), 2026, False),
        (True, date(2027, 1, 1), date(2026, 12, 31), 2027, True),
    ],
)
def test_counts_in_tax_year(paid, paid_at, expense_date, year, expected):
    assert counts_in_tax_year(
        paid=paid, paid_at=paid_at, expense_date=expense_date, year=year,
    ) is expected


def test_open_invoice_style_expense_excluded_from_euer_year():
    """Regression: offene Ausgabe darf die Steueraufstellung nicht aufblasen."""
    assert not counts_in_tax_year(
        paid=False,
        paid_at=None,
        expense_date=date(2026, 6, 15),
        year=2026,
    )


# --------------------------------------------------------------------------- #
# Beschreibungs-Katalog
# --------------------------------------------------------------------------- #


def test_expense_descriptions_are_substantial():
    assert len(EXPENSE_DESCRIPTIONS) >= 300
    folded = [x.casefold() for x in EXPENSE_DESCRIPTIONS]
    assert len(folded) == len(set(folded))
    assert "expense_description" in TAXONOMIES
    assert len(TAXONOMIES["expense_description"]) >= 300


def test_all_descriptions_dedupes_preserving_order():
    out = all_descriptions()
    assert out == list(dict.fromkeys(EXPENSE_DESCRIPTIONS))
    assert len(out) == len(EXPENSE_DESCRIPTIONS)


def test_every_description_has_category_and_vice_versa():
    assert set(EXPENSE_DESCRIPTIONS) == set(EXPENSE_DESCRIPTION_CATEGORY)
    assert len(EXPENSE_DESCRIPTIONS) == len(EXPENSE_DESCRIPTION_CATEGORY)


def test_expense_description_categories_are_valid():
    allowed = {
        "hosting", "domain", "software", "lizenz", "hardware",
        "ki_api", "werbung", "buero", "reise", "sonstige",
    }
    for desc, cat in EXPENSE_DESCRIPTION_CATEGORY.items():
        assert cat in allowed, (desc, cat)


def test_category_coverage_spans_all_expense_kinds():
    """Steueraufstellung braucht alle Kategorien, nicht nur Hosting."""
    counts = Counter(EXPENSE_DESCRIPTION_CATEGORY.values())
    for cat in (
        "hosting", "domain", "software", "lizenz", "hardware",
        "ki_api", "werbung", "buero", "reise", "sonstige",
    ):
        assert counts[cat] >= 10, f"{cat} under-represented: {counts[cat]}"


@pytest.mark.parametrize(
    "needle,expected_cat",
    [
        ("Hetzner Cloud VPS", "hosting"),
        ("Anthropic Claude API Nutzung", "ki_api"),
        ("Hostinger Domain-Registrierung", "domain"),
        ("MacBook Pro 14 Zoll", "hardware"),
        ("Windows Server 2022 Lizenz", "lizenz"),
        ("Google Ads Kampagne", "werbung"),
        ("Bahnfahrt Geschäftsreise", "reise"),
        ("Coworking-Space Tagesticket", "buero"),
        ("GitHub Team Plan", "software"),
        ("Geschäftsessen mit Kunde", "sonstige"),
    ],
)
def test_known_tax_ready_labels_map_to_category(needle, expected_cat):
    assert needle in EXPENSE_DESCRIPTIONS
    assert category_for_description(needle) == expected_cat


def test_category_for_description_casefold():
    sample = next(iter(EXPENSE_DESCRIPTION_CATEGORY))
    expected = EXPENSE_DESCRIPTION_CATEGORY[sample]
    assert category_for_description(sample) == expected
    assert category_for_description(sample.upper()) == expected
    assert category_for_description(sample.swapcase()) == expected
    assert category_for_description("gibt-es-nicht-xyz") is None
    assert category_for_description("") is None


def test_category_for_description_prefers_exact_key():
    # Exact match before fold-scan (same result, but path covers first branch).
    key = "Sonstige Betriebsausgabe"
    assert category_for_description(key) == EXPENSE_DESCRIPTION_CATEGORY[key]


def test_descriptions_are_nonempty_ascii_friendly_bookkeeping_text():
    for d in EXPENSE_DESCRIPTIONS:
        assert d.strip() == d
        assert len(d) >= 3
        assert "\n" not in d
        assert "\t" not in d


def test_merge_suggestions_includes_curated_expense_descriptions():
    values = merge_suggestions("expense_description", {}, q="Hetzner", limit=20)
    assert any("Hetzner" in v for v in values)
    # Eigene Bestandswerte gewinnen bei gleicher Fold-Form
    values2 = merge_suggestions(
        "expense_description",
        {"Mein Hetzner-Sonderposten": 9},
        q="Hetzner",
        limit=20,
    )
    assert values2[0] == "Mein Hetzner-Sonderposten"


def test_merge_suggestions_empty_query_returns_pool():
    values = merge_suggestions("expense_description", {}, q="", limit=50)
    assert len(values) == 50
    assert all(isinstance(v, str) for v in values)


# --------------------------------------------------------------------------- #
# Schema: Create synchronisiert paid + recurrence
# --------------------------------------------------------------------------- #


def test_expense_create_defaults_paid_with_cash_date():
    e = ExpenseCreate(
        description="Test",
        category="software",
        amount=Decimal("12.50"),
        date=date(2026, 7, 1),
    )
    assert e.paid is True
    assert e.paid_at == date(2026, 7, 1)
    assert e.recurrence is None
    assert e.recurring is False


def test_expense_create_unpaid_clears_paid_at():
    e = ExpenseCreate(
        description="Offen",
        category="sonstige",
        amount=Decimal("1"),
        date=date(2026, 7, 1),
        paid=False,
        paid_at=date(2026, 7, 2),
    )
    assert e.paid is False
    assert e.paid_at is None


def test_expense_create_explicit_paid_at_kept():
    e = ExpenseCreate(
        description="Später bezahlt",
        category="hosting",
        amount=Decimal("99"),
        date=date(2026, 1, 10),
        paid=True,
        paid_at=date(2026, 2, 1),
    )
    assert e.paid_at == date(2026, 2, 1)


def test_expense_create_legacy_recurring_becomes_monthly():
    e = ExpenseCreate(
        description="Abo",
        category="software",
        amount=Decimal("10"),
        date=date(2026, 1, 1),
        recurring=True,
    )
    assert e.recurring is True
    assert e.recurrence and e.recurrence.value == "monthly"


def test_expense_create_explicit_recurrence_sets_flag():
    e = ExpenseCreate(
        description="Domain",
        category="domain",
        amount=Decimal("15"),
        date=date(2026, 1, 1),
        recurrence="yearly",
    )
    assert e.recurring is True
    assert e.recurrence.value == "yearly"


def test_expense_payment_update_schema():
    u = ExpensePaymentUpdate(paid=True, paid_at=date(2026, 8, 1))
    assert u.paid is True and u.paid_at == date(2026, 8, 1)
    u2 = ExpensePaymentUpdate(paid=False)
    assert u2.paid is False and u2.paid_at is None


def test_tax_year_matrix_matches_schema_normalized_create():
    """Nach Create-Validator gilt dieselbe Cash-Jahr-Logik wie in der EÜR."""
    open_e = ExpenseCreate(
        description="x", category="sonstige", amount=1, date=date(2026, 5, 1), paid=False,
    )
    assert not counts_in_tax_year(
        paid=open_e.paid, paid_at=open_e.paid_at, expense_date=open_e.date, year=2026,
    )
    paid_e = ExpenseCreate(
        description="y", category="sonstige", amount=1,
        date=date(2026, 5, 1), paid=True, paid_at=date(2025, 12, 20),
    )
    assert counts_in_tax_year(
        paid=paid_e.paid, paid_at=paid_e.paid_at, expense_date=paid_e.date, year=2025,
    )
    assert not counts_in_tax_year(
        paid=paid_e.paid, paid_at=paid_e.paid_at, expense_date=paid_e.date, year=2026,
    )
