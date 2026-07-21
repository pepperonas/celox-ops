"""Gutschrift/Storno — DB-freie Tests der reinen Service-Logik.

Deckt die drei Dinge ab, die am Storno wirklich weh tun, wenn sie falsch sind:
Beträge (Spiegelbild), Nummernkreis (eigene GS-Sequenz) und die Statuswahl
(sie entscheidet, ob EÜR/Dashboard nach dem Storno noch stimmen).
"""
from decimal import Decimal

from app.models.invoice import InvoiceStatus
from app.services.invoice_service import (
    build_credit_note_positions,
    credit_note_statuses,
    next_credit_note_number,
)


class TestBuildCreditNotePositions:
    def test_prices_are_negated(self):
        out = build_credit_note_positions([
            {"position": 1, "beschreibung": "Beratung", "menge": "2",
             "einheit": "Std", "einzelpreis": "95.00", "gesamt": "190.00"},
        ])
        assert out[0]["einzelpreis"] == "-95.00"
        assert out[0]["gesamt"] == "-190.00"

    def test_quantity_and_text_untouched(self):
        out = build_credit_note_positions([
            {"position": 1, "beschreibung": "Beratung", "menge": "2",
             "einheit": "Std", "einzelpreis": "95.00", "gesamt": "190.00"},
        ])
        assert out[0]["menge"] == "2"
        assert out[0]["einheit"] == "Std"
        assert out[0]["beschreibung"] == "Beratung"
        assert out[0]["position"] == 1

    def test_already_negative_stays_negative(self):
        # -abs: eine Gutschrift auf eine Gutschrift dreht nie zurück ins Plus
        out = build_credit_note_positions([
            {"einzelpreis": "-95.00", "gesamt": "-190.00"},
        ])
        assert out[0]["einzelpreis"] == "-95.00"
        assert out[0]["gesamt"] == "-190.00"

    def test_no_float_rounding_error(self):
        # 0.1+0.2-Klassiker: über Decimal/str darf nichts driften
        out = build_credit_note_positions([{"einzelpreis": "1234.10", "gesamt": "3702.30"}])
        assert Decimal(out[0]["gesamt"]) == Decimal("-3702.30")
        assert Decimal(out[0]["einzelpreis"]) == Decimal("-1234.10")

    def test_zero_stays_zero(self):
        out = build_credit_note_positions([{"einzelpreis": "0", "gesamt": "0.00"}])
        assert Decimal(out[0]["gesamt"]) == Decimal("0")

    def test_missing_and_none_fields_tolerated(self):
        out = build_credit_note_positions([{"beschreibung": "Nur Text"}, {"einzelpreis": None}])
        assert out[0] == {"beschreibung": "Nur Text"}
        assert out[1]["einzelpreis"] is None

    def test_empty_list(self):
        assert build_credit_note_positions([]) == []

    def test_original_not_mutated(self):
        original = [{"einzelpreis": "95.00", "gesamt": "190.00"}]
        build_credit_note_positions(original)
        assert original[0]["einzelpreis"] == "95.00"


class TestNextCreditNoteNumber:
    def test_first_number(self):
        assert next_credit_note_number(set(), 2026) == "GS-2026-0001"

    def test_continues_sequence(self):
        assert next_credit_note_number({1, 2, 3}, 2026) == "GS-2026-0004"

    def test_fills_gap(self):
        # gelöschte Gutschrift verbrennt keine Nummer
        assert next_credit_note_number({1, 3}, 2026) == "GS-2026-0002"

    def test_zero_padded_beyond_nine(self):
        assert next_credit_note_number(set(range(1, 10)), 2026) == "GS-2026-0010"
        assert next_credit_note_number(set(range(1, 100)), 2026) == "GS-2026-0100"

    def test_accepts_list(self):
        assert next_credit_note_number([1, 2], 2026) == "GS-2026-0003"

    def test_separate_from_invoice_numbers(self):
        # Eigener Kreis: die GS-Nummer kollidiert nie mit CO-… und startet je Jahr neu
        assert next_credit_note_number(set(), 2027).startswith("GS-2027-")


class TestCreditNoteStatuses:
    def test_paid_original_nets_out(self):
        # Geld ist geflossen und fließt zurück → beide bezahlt, Summe 0 in der EÜR
        gs, orig = credit_note_statuses(InvoiceStatus.bezahlt)
        assert gs == InvoiceStatus.bezahlt
        assert orig == InvoiceStatus.bezahlt

    def test_unpaid_original_is_neutralised(self):
        # Nie Geld geflossen → beide raus aus allen Zahlen, Forderung entfällt
        for status in (InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig):
            gs, orig = credit_note_statuses(status)
            assert gs == InvoiceStatus.storniert, status
            assert orig == InvoiceStatus.storniert, status

    def test_unpaid_never_creates_phantom_revenue(self):
        # Regression: die Gutschrift darf bei unbezahltem Original NICHT
        # `bezahlt` werden — das erzeugte einen negativen Umsatz aus dem Nichts.
        gs, _ = credit_note_statuses(InvoiceStatus.gestellt)
        assert gs != InvoiceStatus.bezahlt
