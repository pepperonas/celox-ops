"""Zahlungsstand und Ausgaben-Beschreibungs-Taxonomie."""
from app.data.expense_descriptions import (
    EXPENSE_DESCRIPTION_CATEGORY,
    EXPENSE_DESCRIPTIONS,
    category_for_description,
)
from app.services.expense_payment import normalize_payment
from app.services.taxonomy import TAXONOMIES
from datetime import date


def test_normalize_payment_unpaid_clears_date():
    assert normalize_payment(paid=False, paid_at=date(2026, 1, 5), expense_date=date(2026, 1, 1)) == (
        False, None,
    )


def test_normalize_payment_paid_falls_back_to_expense_date():
    d = date(2026, 3, 15)
    assert normalize_payment(paid=True, paid_at=None, expense_date=d) == (True, d)


def test_normalize_payment_keeps_explicit_paid_at():
    assert normalize_payment(
        paid=True, paid_at=date(2026, 4, 1), expense_date=date(2026, 3, 1),
    ) == (True, date(2026, 4, 1))


def test_expense_descriptions_are_substantial():
    assert len(EXPENSE_DESCRIPTIONS) >= 300
    folded = [x.casefold() for x in EXPENSE_DESCRIPTIONS]
    assert len(folded) == len(set(folded))
    assert "expense_description" in TAXONOMIES
    assert len(TAXONOMIES["expense_description"]) >= 300


def test_expense_description_categories_are_valid():
    allowed = {
        "hosting", "domain", "software", "lizenz", "hardware",
        "ki_api", "werbung", "buero", "reise", "sonstige",
    }
    assert len(EXPENSE_DESCRIPTION_CATEGORY) >= 150
    for desc, cat in EXPENSE_DESCRIPTION_CATEGORY.items():
        assert cat in allowed, (desc, cat)
        assert desc in EXPENSE_DESCRIPTIONS or desc.casefold() in {
            x.casefold() for x in EXPENSE_DESCRIPTIONS
        }


def test_category_for_description_casefold():
    sample = next(iter(EXPENSE_DESCRIPTION_CATEGORY))
    expected = EXPENSE_DESCRIPTION_CATEGORY[sample]
    assert category_for_description(sample) == expected
    assert category_for_description(sample.upper()) == expected
    assert category_for_description("gibt-es-nicht-xyz") is None
