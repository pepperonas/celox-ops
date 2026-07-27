"""DB-freie Tests für die Unveränderlichkeit gestellter Rechnungen (GoBD)."""
from datetime import date
from decimal import Decimal

from app.services.invoice_lock import (
    FIELD_LABELS,
    changed_locked_fields,
    is_locked,
    lock_error,
)

_CURRENT = {
    "customer_id": "11111111-1111-1111-1111-111111111111",
    "title": "Beratung Juli",
    "positions": [{"beschreibung": "Beratung", "menge": Decimal("10"),
                   "einzelpreis": Decimal("95.00"), "gesamt": Decimal("950.00")}],
    "tax_rate": Decimal("19.00"),
    "tax_exempt": False,
    "invoice_date": date(2026, 7, 1),
    "due_date": date(2026, 7, 15),
    "notes": "Zahlbar ohne Abzug.",
    "discount_type": None,
    "discount_value": None,
    "discount_reason": None,
    "include_activity_chart": False,
}


# ---- Status ----------------------------------------------------------------
def test_only_draft_is_editable():
    assert is_locked("entwurf") is False
    for status in ("gestellt", "bezahlt", "ueberfaellig", "storniert"):
        assert is_locked(status) is True, status


def test_is_locked_accepts_enum_like():
    class _S:
        value = "gestellt"
    assert is_locked(_S()) is True


# ---- Erkennung echter Änderungen ------------------------------------------
def test_unchanged_payload_passes():
    """Ein Formular, das den Datensatz unverändert zurücksendet, darf nicht scheitern."""
    same = {
        "title": "Beratung Juli",
        "tax_rate": "19.00",                     # String aus dem JSON
        "invoice_date": "2026-07-01",            # ISO-String
        "tax_exempt": False,
        "notes": "Zahlbar ohne Abzug.",
        "discount_type": None,
        "discount_value": None,
        "include_activity_chart": False,
    }
    assert changed_locked_fields(_CURRENT, same) == []


def test_amount_change_is_detected():
    assert changed_locked_fields(_CURRENT, {"tax_rate": "7.00"}) == ["tax_rate"]
    assert changed_locked_fields(_CURRENT, {"tax_exempt": True}) == ["tax_exempt"]


def test_position_change_is_detected():
    changed = [{"beschreibung": "Beratung", "menge": "12",
                "einzelpreis": "95.00", "gesamt": "1140.00"}]
    assert changed_locked_fields(_CURRENT, {"positions": changed}) == ["positions"]


def test_identical_positions_with_string_decimals_pass():
    same = [{"beschreibung": "Beratung", "menge": "10",
             "einzelpreis": "95.00", "gesamt": "950.00"}]
    assert changed_locked_fields(_CURRENT, {"positions": same}) == []


def test_added_discount_is_detected():
    blocked = changed_locked_fields(_CURRENT, {"discount_type": "percent", "discount_value": 10})
    assert set(blocked) == {"discount_type", "discount_value"}


def test_notes_are_locked_because_they_are_printed():
    # `notes` erscheint im PDF als „Hinweis:" → nach dem Stellen tabu.
    assert changed_locked_fields(_CURRENT, {"notes": "Neuer Text"}) == ["notes"]


def test_customer_reassignment_is_detected():
    other = "22222222-2222-2222-2222-222222222222"
    assert changed_locked_fields(_CURRENT, {"customer_id": other}) == ["customer_id"]


def test_empty_string_equals_none():
    """Formulare senden "" für leere Felder — das ist keine Änderung gegenüber NULL."""
    assert changed_locked_fields(_CURRENT, {"discount_reason": ""}) == []


def test_non_content_fields_are_ignored():
    """Status/Zahlung/Mahnstufe laufen über eigene Endpunkte, nicht über PUT."""
    assert changed_locked_fields(_CURRENT, {"status": "bezahlt", "amount_paid": 950,
                                            "reminder_level": 2, "pdf_path": "/x.pdf"}) == []


def test_dates_compare_across_types():
    assert changed_locked_fields(_CURRENT, {"due_date": "2026-07-15"}) == []
    assert changed_locked_fields(_CURRENT, {"due_date": "2026-08-15"}) == ["due_date"]


# ---- Fehlermeldung ---------------------------------------------------------
def test_error_names_fields_and_the_correct_path():
    msg = lock_error(["positions", "tax_rate"])
    assert "Positionen" in msg and "Steuersatz" in msg
    assert "Gutschrift" in msg and "Duplizieren" in msg


def test_error_truncates_long_field_lists():
    msg = lock_error(list(FIELD_LABELS)[:8])
    assert "…" in msg


# ---- Vollständigkeit gegen das Schema -------------------------------------
def test_every_updatable_content_field_is_covered():
    """Neues Feld in InvoiceUpdate ⇒ hier eintragen, sonst wäre es unbemerkt
    nach dem Stellen änderbar."""
    from app.schemas.invoice import InvoiceUpdate

    assert set(InvoiceUpdate.model_fields) == set(FIELD_LABELS)
