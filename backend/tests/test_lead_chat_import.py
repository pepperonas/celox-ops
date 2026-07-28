"""DB-/netzfreie Tests für den Chat-Import (Lead per KI aus Gesprächsmaterial).

Schwerpunkt sind die Regeln, die im **Code** durchgesetzt werden und nicht nur im
Prompt stehen: Belegzwang, Dedup/Idempotenz, Notizen anfügen statt ersetzen, und
dass importierte Historie keine Punkte vergibt.
"""
import inspect
from datetime import date

import pytest

import app.models.rainmaker_activity  # noqa: F401 — Mapper-Ziel von RainmakerLead
from app.models.rainmaker_lead import RainmakerLeadStatus
from app.services.lead_chat_import import (
    EVIDENCE_REQUIRED,
    MAX_IMAGES,
    PROMPT_VERSION,
    activity_fingerprint,
    activity_note,
    append_notes,
    build_proposal,
    build_user_content,
    existing_fingerprints,
    material_hash,
    notes_block,
    select_items,
)


class _Lead:
    company = "Muster Elektro GmbH"
    contact_name = None
    role = None
    decision_maker = None
    employee_count = None
    email = None
    phone = None
    website = "https://muster.de"
    target = None
    tags = None
    status = RainmakerLeadStatus.new
    notes = "Handgepflegte Notiz vom Telefonat."
    activities: list = []


class _Activity:
    def __init__(self, notes):
        self.notes = notes


TODAY = date(2026, 7, 28)

_AI = {
    "summary": "Kunde fragt nach Referenzen.",
    "notes_lines": ["Braucht Angebot bis Ende August", "Budget ca. 15k bestätigt"],
    "activities": [
        {"type": "call", "occurred_on": "2026-07-20", "direction": "eingehend",
         "excerpt": "Herr Meier ruft an, fragt nach Referenzen für die BCS-Anbindung."},
        {"type": "email", "occurred_on": "2026-07-22", "direction": "ausgehend",
         "excerpt": "Referenzliste versendet, Rückfrage zu Schnittstellen offen."},
    ],
    "next_action": {"type": "follow_up", "due_date": "2026-08-05",
                    "reason": "Kunde bat um Rückmeldung nach dem Urlaub"},
    "fields": [
        {"field": "contact_name", "value": "Thomas Meier",
         "evidence": "Mit freundlichen Grüßen, Thomas Meier"},
        {"field": "email", "value": "t.meier@muster.de",
         "evidence": "t.meier@muster.de"},
    ],
}


# --------------------------------------------------------------------------- #
#  Regel 1: nichts erfinden — Belegzwang wird im Code durchgesetzt
# --------------------------------------------------------------------------- #
class TestEvidenceEnforced:
    def test_field_without_evidence_is_dropped_and_reported(self):
        ai = {**_AI, "fields": [{"field": "employee_count", "value": 50}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert [f["field"] for f in p["fields"]] == []
        assert any(i["field"] == "employee_count" and "Beleg" in i["reason"]
                   for i in p["ignored"]), p["ignored"]

    def test_too_short_evidence_counts_as_none(self):
        ai = {**_AI, "fields": [{"field": "role", "value": "Geschäftsführung", "evidence": "GF"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["fields"] == []
        assert p["ignored"]

    def test_every_field_requires_evidence(self):
        """Kein Feld darf sich der Belegpflicht entziehen."""
        from app.services.lead_chat_import import _FIELD_LABELS
        assert EVIDENCE_REQUIRED == set(_FIELD_LABELS)

    def test_field_outside_the_whitelist_is_refused(self):
        ai = {**_AI, "fields": [{"field": "value_estimate", "value": 9999, "evidence": "Budget 9999"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["fields"] == []
        assert any("nicht freigegeben" in i["reason"] for i in p["ignored"])

    def test_unparseable_employee_count_is_not_guessed(self):
        ai = {**_AI, "fields": [{"field": "employee_count", "value": "ca. 50-100",
                                 "evidence": "wir sind ein mittelständischer Betrieb"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["fields"] == []
        assert any(i["field"] == "employee_count" for i in p["ignored"])

    def test_real_number_passes(self):
        ai = {**_AI, "fields": [{"field": "employee_count", "value": 42,
                                 "evidence": "wir haben 42 Mitarbeiter"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["fields"][0]["value"] == 42


# --------------------------------------------------------------------------- #
#  Aktivitäten: Datum, Zukunft, Typ
# --------------------------------------------------------------------------- #
class TestActivities:
    def test_activities_are_proposed_with_prefix_and_direction(self):
        p = build_proposal(_AI, _Lead(), today=TODAY)
        assert len(p["activities"]) == 2
        first = p["activities"][0]
        assert first["type"] == "call" and first["day"] == "2026-07-20"
        assert first["note"].startswith("[KI aus Chat, 2026-07-20 · ")
        assert "eingehend:" in first["note"]
        assert "Referenzen" in first["note"]

    def test_activity_without_date_is_ignored_not_guessed(self):
        ai = {**_AI, "activities": [{"type": "call", "excerpt": "irgendwann telefoniert"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["activities"] == []
        assert any("Datum" in i["reason"] for i in p["ignored"])

    def test_future_dated_activity_is_ignored(self):
        ai = {**_AI, "activities": [{"type": "call", "occurred_on": "2026-09-01",
                                     "excerpt": "Termin"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["activities"] == []
        assert any("Zukunft" in i["reason"] for i in p["ignored"])

    def test_unknown_activity_type_is_ignored(self):
        ai = {**_AI, "activities": [{"type": "telepathie", "occurred_on": "2026-07-20",
                                     "excerpt": "x" * 20}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["activities"] == []

    def test_next_action_needs_type_and_date(self):
        p = build_proposal({**_AI, "next_action": {"type": "call"}}, _Lead(), today=TODAY)
        assert p["next_action"] is None
        assert any(i["field"] == "next_action" for i in p["ignored"])

    def test_only_one_next_action(self):
        p = build_proposal(_AI, _Lead(), today=TODAY)
        assert isinstance(p["next_action"], dict)


# --------------------------------------------------------------------------- #
#  Regel 4: Idempotenz
# --------------------------------------------------------------------------- #
class TestIdempotency:
    def test_fingerprint_is_stable_and_type_sensitive(self):
        a = activity_fingerprint("call", "2026-07-20", "Herr Meier ruft an")
        b = activity_fingerprint("call", "2026-07-20", "  HERR   MEIER RUFT AN  ")
        assert a == b, "Groß-/Kleinschreibung und Leerraum dürfen nicht zählen"
        assert a != activity_fingerprint("email", "2026-07-20", "Herr Meier ruft an")
        assert a != activity_fingerprint("call", "2026-07-21", "Herr Meier ruft an")

    def test_fingerprint_survives_a_different_tail(self):
        """Kappt das Modell den Auszug anders, bleibt der Schlüssel gleich.

        Der Schlüssel deckt nur die ersten FINGERPRINT_SOURCE_CHARS Zeichen ab —
        deshalb ist der gemeinsame Anfang hier länger als diese Grenze."""
        from app.services.lead_chat_import import FINGERPRINT_SOURCE_CHARS

        head = ("Herr Meier ruft an und fragt nach Referenzen für die Anbindung an das "
                "bestehende System, weil der Betriebsrat vorher ein Votum abgeben möchte "
                "und die Geschäftsführung das so entschieden hat, ")
        assert len(head) > FINGERPRINT_SOURCE_CHARS
        assert activity_fingerprint("call", "2026-07-20", head + "nachfragt.") == \
               activity_fingerprint("call", "2026-07-20", head + "ein Votum will.")

    def test_second_run_marks_duplicates_and_does_not_preselect(self):
        p1 = build_proposal(_AI, _Lead(), today=TODAY)
        existing = [_Activity(a["note"]) for a in p1["activities"]]
        p2 = build_proposal(_AI, _Lead(), existing_activities=existing, today=TODAY)
        assert all(a["duplicate"] for a in p2["activities"])
        assert not any(a["preselected"] for a in p2["activities"])

    def test_duplicates_inside_one_batch_are_flagged(self):
        ai = {**_AI, "activities": [_AI["activities"][0], dict(_AI["activities"][0])]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert [a["duplicate"] for a in p["activities"]] == [False, True]

    def test_existing_fingerprints_reads_the_prefix(self):
        note = activity_note("2026-07-20", "eingehend", "Text", "abc123")
        assert existing_fingerprints([_Activity(note)]) == {"abc123"}
        assert existing_fingerprints([_Activity("normale Notiz")]) == set()

    def test_material_hash_covers_prompt_version_and_material(self):
        lead = _Lead()
        base = material_hash("verlauf", ["d1"], lead, "claude-sonnet-5", "1")
        assert base == material_hash("verlauf", ["d1"], lead, "claude-sonnet-5", "1")
        assert base != material_hash("anderer verlauf", ["d1"], lead, "claude-sonnet-5", "1")
        assert base != material_hash("verlauf", ["d2"], lead, "claude-sonnet-5", "1")
        assert base != material_hash("verlauf", ["d1"], lead, "claude-haiku-4-5-20251001", "1")
        assert base != material_hash("verlauf", ["d1"], lead, "claude-sonnet-5", "2"), \
            "Prompt-Änderung muss gespeicherte Vorschläge verwerfen"

    def test_material_hash_is_order_independent_for_images(self):
        lead = _Lead()
        assert material_hash("x", ["a", "b"], lead, "m") == material_hash("x", ["b", "a"], lead, "m")

    def test_material_hash_follows_the_lead_state(self):
        lead, other = _Lead(), _Lead()
        other.contact_name = "Thomas Meier"
        assert material_hash("x", [], lead, "m") != material_hash("x", [], other, "m")


# --------------------------------------------------------------------------- #
#  Notizen: anfügen, nie ersetzen
# --------------------------------------------------------------------------- #
class TestNotes:
    def test_existing_notes_are_kept_in_front(self):
        block = notes_block(["Punkt A", "Punkt B"], "28.07.2026")
        result = append_notes("Handgepflegt.", block)
        assert result.startswith("Handgepflegt.")
        assert "— aus Chat, 28.07.2026 —" in result
        assert "- Punkt A" in result and "- Punkt B" in result

    def test_empty_block_leaves_notes_untouched(self):
        assert append_notes("Bestand", notes_block([], "28.07.2026")) == "Bestand"

    def test_works_without_previous_notes(self):
        assert append_notes(None, notes_block(["A"], "28.07.2026")).startswith("— aus Chat")

    def test_unchanged_value_is_reported_as_such(self):
        lead = _Lead()
        lead.contact_name = "Thomas Meier"
        p = build_proposal(_AI, lead, today=TODAY)
        assert "contact_name" not in [f["field"] for f in p["fields"]]
        assert any("steht schon so" in i["reason"] for i in p["ignored"])


# --------------------------------------------------------------------------- #
#  Regel 6: Status nur vorschlagen
# --------------------------------------------------------------------------- #
class TestStatus:
    def test_status_is_never_preselected(self):
        ai = {**_AI, "fields": [{"field": "status", "value": "in_conversation",
                                 "evidence": "wir sind im Gespräch"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["fields"][0]["field"] == "status"
        assert p["fields"][0]["preselected"] is False

    def test_invalid_status_is_dropped(self):
        ai = {**_AI, "fields": [{"field": "status", "value": "vielleicht",
                                 "evidence": "irgendwas dazwischen"}]}
        p = build_proposal(ai, _Lead(), today=TODAY)
        assert p["fields"] == []

    def test_other_fields_are_preselected(self):
        p = build_proposal(_AI, _Lead(), today=TODAY)
        assert all(f["preselected"] for f in p["fields"])


# --------------------------------------------------------------------------- #
#  Auswahl anwenden
# --------------------------------------------------------------------------- #
class TestSelection:
    def test_only_selected_keys_are_returned(self):
        p = build_proposal(_AI, _Lead(), today=TODAY)
        picked = select_items(p, [p["activities"][0]["key"], p["fields"][0]["key"]])
        assert len(picked["activities"]) == 1
        assert len(picked["fields"]) == 1
        assert picked["note_lines"] == [] and picked["next_action"] is None

    def test_unknown_keys_cannot_force_anything(self):
        p = build_proposal(_AI, _Lead(), today=TODAY)
        picked = select_items(p, ["field:owner_id", "act:999", "erfunden"])
        assert picked == {"note_lines": [], "activities": [], "next_action": None, "fields": []}

    def test_empty_selection_writes_nothing(self):
        picked = select_items(build_proposal(_AI, _Lead(), today=TODAY), [])
        assert not any(picked.values())


# --------------------------------------------------------------------------- #
#  Vision-Eingabe
# --------------------------------------------------------------------------- #
class TestUserContent:
    def test_images_come_before_the_text(self):
        blocks = build_user_content("Verlauf", [
            {"media_type": "image/png", "b64": "AAA"},
            {"media_type": "image/jpeg", "b64": "BBB"},
        ], _Lead())
        assert [b["type"] for b in blocks] == ["image", "image", "text"]
        assert blocks[0]["source"]["media_type"] == "image/png"
        assert "2 Screenshot(s)" in blocks[-1]["text"]

    def test_lead_context_is_marked_as_no_evidence(self):
        text = build_user_content("Verlauf", [], _Lead())[-1]["text"]
        assert "nicht als Beleg" in text
        assert "Muster Elektro GmbH" in text

    def test_text_only_works(self):
        blocks = build_user_content("Nur Text", [], _Lead())
        assert [b["type"] for b in blocks] == ["text"]
        assert "Nur Text" in blocks[0]["text"]


# --------------------------------------------------------------------------- #
#  Regel 2: importierte Historie vergibt KEINE Punkte
# --------------------------------------------------------------------------- #
def _code_without_docstring(func) -> str:
    """Quelltext ohne Docstring — der Guard soll den CODE prüfen, nicht die
    Kommentare, die den Fehler ja gerade beschreiben."""
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    node = tree.body[0]
    body = node.body[1:] if (node.body and isinstance(node.body[0], ast.Expr)
                             and isinstance(node.body[0].value, ast.Constant)) else node.body
    return "\n".join(ast.unparse(stmt) for stmt in body)


class TestNoGamificationForImportedHistory:
    def test_apply_neither_awards_points_nor_uses_the_complete_endpoint(self):
        """Der Import legt erledigte Aktivitäten DIREKT an. Ginge er über
        `/activities/{id}/complete`, würden Punkte/Streak verfälscht und der
        Next-Action-Zwang liefe in einen 400er."""
        from app.routers import rainmaker

        code = _code_without_docstring(rainmaker.chat_import_apply)
        assert "register_completion" not in code
        assert "/complete" not in code and "complete_activity" not in code
        assert "RainmakerActivityStatus.done" in code
        assert "completed_at" in code

    def test_undo_takes_no_foreign_ids(self):
        """Die Rücknahme darf kein Löschwerkzeug sein: sie liest die IDs aus dem
        eigenen Protokoll, nicht aus dem Request."""
        from app.routers import rainmaker

        code = _code_without_docstring(rainmaker.chat_import_undo)
        assert "activity_ids" in code
        assert "RainmakerActivity.lead_id == lead.id" in code   # doppelt gesichert
        assert "UserRole.mitarbeiter" in code                   # eigener Lauf nur


# --------------------------------------------------------------------------- #
#  Grenzen
# --------------------------------------------------------------------------- #
def test_caps_are_conservative():
    assert 1 <= MAX_IMAGES <= 10
    assert PROMPT_VERSION.isdigit()


@pytest.mark.parametrize("value,expected", [(None, "—"), ("", "—"), ("x", "x")])
def test_display_of_empty_values(value, expected):
    from app.services.lead_chat_import import _display
    assert _display(value) == expected
