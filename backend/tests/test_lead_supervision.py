"""Aufsichtslogik: Diff, Rücknahme, Tagesdeckel — alles DB-frei."""
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.user import TRASH_RETENTION_DAYS, VERKAEUFER_DAILY_DELETE_CAP
from app.services.lead_supervision import (
    TRACKED_FIELDS,
    cap_message,
    delete_cap_left,
    diff_fields,
    revert_plan,
)


class TestDiff:
    def test_only_real_changes_are_logged(self):
        before = {"company": "Alpha", "status": "new", "notes": "x"}
        after = {"company": "Alpha GmbH", "status": "new", "notes": "x"}
        assert diff_fields(before, after) == {
            "company": {"old": "Alpha", "new": "Alpha GmbH"}
        }

    def test_unchanged_form_submit_logs_nothing(self):
        # Das Formular sendet alle Felder zurück. Würde man Anwesenheit statt
        # Wert vergleichen, wäre jedes Speichern ein 16-Feld-Eintrag und die
        # Rücknahme würde unbeteiligte Felder mitdrehen.
        snap = {f: "gleich" for f in TRACKED_FIELDS}
        assert diff_fields(snap, dict(snap)) == {}

    def test_fields_absent_from_the_request_are_ignored(self):
        # PUT mit exclude_unset → nur gesendete Felder dürfen zählen.
        before = {"company": "Alpha", "notes": "wichtig"}
        assert diff_fields(before, {"company": "Beta"}) == {
            "company": {"old": "Alpha", "new": "Beta"}
        }

    def test_untracked_fields_never_appear(self):
        before = {"email_norm": "a@b.de", "updated_at": "gestern"}
        after = {"email_norm": "c@d.de", "updated_at": "heute"}
        assert diff_fields(before, after) == {}

    def test_decimal_date_and_enum_become_json_safe(self):
        class FakeStatus:
            value = "contacted"

        out = diff_fields(
            {"value_estimate": Decimal("1000.00"), "status": "new", "notes": None},
            {"value_estimate": Decimal("2500.50"), "status": FakeStatus(), "notes": "neu"},
        )
        assert out["value_estimate"] == {"old": "1000.00", "new": "2500.50"}
        assert out["status"] == {"old": "new", "new": "contacted"}
        assert out["notes"] == {"old": None, "new": "neu"}

    def test_dates_are_serialised(self):
        out = diff_fields({"notes": date(2026, 7, 1)}, {"notes": datetime(
            2026, 7, 2, 10, 0, tzinfo=timezone.utc)})
        assert out["notes"]["old"] == "2026-07-01"
        assert out["notes"]["new"].startswith("2026-07-02T10:00")

    def test_tag_lists_compare_by_content(self):
        assert diff_fields({"tags": ["a", "b"]}, {"tags": ["a", "b"]}) == {}
        assert diff_fields({"tags": ["a"]}, {"tags": ["a", "b"]})["tags"] == {
            "old": ["a"], "new": ["a", "b"]
        }


class TestRevert:
    def test_restores_old_values(self):
        changes = {"company": {"old": "Alpha", "new": "Beta"}}
        apply, conflicts = revert_plan(changes, {"company": "Beta"})
        assert apply == {"company": "Alpha"}
        assert conflicts == []

    def test_field_changed_since_is_a_conflict_not_an_overwrite(self):
        # Hat jemand anders inzwischen gearbeitet, würde ein blindes Zurückdrehen
        # dessen Arbeit stillschweigend löschen.
        changes = {"company": {"old": "Alpha", "new": "Beta"}}
        apply, conflicts = revert_plan(changes, {"company": "Gamma"})
        assert apply == {}
        assert conflicts == ["company"]

    def test_partial_revert_is_possible(self):
        changes = {
            "company": {"old": "Alpha", "new": "Beta"},
            "notes": {"old": "alt", "new": "neu"},
        }
        apply, conflicts = revert_plan(changes, {"company": "Beta", "notes": "von Hand"})
        assert apply == {"company": "Alpha"}
        assert conflicts == ["notes"]

    def test_unknown_field_is_never_written_back(self):
        # Schutz gegen manipulierte/veraltete Protokollzeilen.
        apply, conflicts = revert_plan(
            {"is_active": {"old": True, "new": False}}, {"is_active": False}
        )
        assert apply == {}
        assert conflicts == []

    def test_decimal_current_value_matches_logged_string(self):
        # Im Protokoll steht "1000.00" (JSON), am Lead ein Decimal — ohne
        # Normalisierung gälte jedes Geldfeld immer als Konflikt.
        changes = {"value_estimate": {"old": "500.00", "new": "1000.00"}}
        apply, conflicts = revert_plan(changes, {"value_estimate": Decimal("1000.00")})
        assert apply == {"value_estimate": "500.00"}
        assert conflicts == []


class TestCap:
    def test_counts_down(self):
        assert delete_cap_left(0, 10) == 10
        assert delete_cap_left(7, 10) == 3
        assert delete_cap_left(10, 10) == 0

    def test_never_negative_even_if_overshot(self):
        # Zwei parallele Requests können den Deckel um eins reißen; das darf
        # nicht in eine negative Restanzeige laufen.
        assert delete_cap_left(12, 10) == 0
        assert delete_cap_left(-3, 10) == 10

    def test_message_names_the_limit_and_a_way_out(self):
        msg = cap_message(VERKAEUFER_DAILY_DELETE_CAP)
        assert str(VERKAEUFER_DAILY_DELETE_CAP) in msg
        assert "Kontoinhaber" in msg and "Papierkorb" in msg


class TestConstants:
    def test_cap_and_retention_are_sane(self):
        assert 1 <= VERKAEUFER_DAILY_DELETE_CAP <= 100
        assert TRASH_RETENTION_DAYS >= 7        # kürzer wäre kein Sicherheitsnetz

    def test_tracked_fields_exist_on_the_model(self):
        from app.models.rainmaker_lead import RainmakerLead

        for field in TRACKED_FIELDS:
            assert hasattr(RainmakerLead, field), f"{field} gibt es am Lead nicht"

    def test_tracked_fields_are_writable_via_the_update_schema(self):
        """Ein protokolliertes Feld, das das Update-Schema nicht kennt, kann sich
        nie ändern — der Eintrag wäre toter Ballast, die Rücknahme wirkungslos."""
        from app.schemas.rainmaker import RainmakerLeadUpdate

        unknown = [f for f in TRACKED_FIELDS if f not in RainmakerLeadUpdate.model_fields]
        assert unknown == []
