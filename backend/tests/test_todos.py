"""To-dos — DB-freie Tests (Modell-Defaults, Schema-Regeln, Taxonomie).

Die Endpunkte selbst brauchen eine DB und werden hier bewusst nicht getestet
(Repo-Konvention: alle Tests laufen ohne Datenbank).
"""
import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.models.todo import Todo, TodoPriority, TodoStatus
from app.schemas.todo import TodoCreate, TodoToggle, TodoUpdate
from app.services.taxonomy import TAXONOMIES, canonicalize, fold


class TestTodoModel:
    def test_defaults(self):
        todo = Todo(title="Angebot nachfassen")
        assert todo.title == "Angebot nachfassen"
        # Python-seitige Defaults greifen erst beim Flush; hier zählt, dass die
        # Spalten existieren und die Enums die erwarteten Werte tragen.
        assert TodoStatus.offen.value == "offen"
        assert TodoStatus.erledigt.value == "erledigt"
        assert [p.value for p in TodoPriority] == ["niedrig", "normal", "hoch"]

    def test_reference_columns_are_nullable(self):
        # Freies To-do ohne Bezug muss möglich sein
        assert Todo.__table__.c.customer_id.nullable is True
        assert Todo.__table__.c.lead_id.nullable is True
        assert Todo.__table__.c.due_date.nullable is True

    def test_reference_fks_use_set_null(self):
        # Ein gelöschter Kunde/Lead darf das To-do nicht mitreißen
        for col in ("customer_id", "lead_id"):
            fks = list(Todo.__table__.c[col].foreign_keys)
            assert fks, col
            assert fks[0].ondelete == "SET NULL", col

    def test_is_owner_scoped(self):
        # Multi-Tenancy: ohne owner_id wäre die Liste global sichtbar
        assert "owner_id" in Todo.__table__.c


class TestTodoSchemas:
    def test_create_minimal(self):
        data = TodoCreate(title="Rechnung stellen")
        assert data.priority == TodoPriority.normal
        assert data.customer_id is None and data.lead_id is None
        assert data.due_date is None

    def test_title_required_and_non_empty(self):
        with pytest.raises(ValidationError):
            TodoCreate(title="")
        with pytest.raises(ValidationError):
            TodoCreate()

    def test_title_length_capped(self):
        with pytest.raises(ValidationError):
            TodoCreate(title="x" * 501)
        assert TodoCreate(title="x" * 500).title

    def test_full_payload(self):
        cid = uuid.uuid4()
        data = TodoCreate(
            title="Vertrag prüfen", notes="vor Verlängerung",
            customer_id=cid, due_date=date(2026, 8, 1), priority=TodoPriority.hoch,
        )
        assert data.customer_id == cid
        assert data.priority == TodoPriority.hoch

    def test_update_is_partial(self):
        # exclude_unset trägt die Presence-Semantik im Router (null löscht Bezug)
        upd = TodoUpdate(title="Neu")
        assert upd.model_dump(exclude_unset=True) == {"title": "Neu"}
        cleared = TodoUpdate(customer_id=None)
        assert cleared.model_dump(exclude_unset=True) == {"customer_id": None}

    def test_toggle_requires_explicit_target(self):
        # Zieltreu statt Flip: doppelter Klick/Retry öffnet nichts versehentlich
        assert TodoToggle(done=True).done is True
        assert TodoToggle(done=False).done is False
        with pytest.raises(ValidationError):
            TodoToggle()


class TestTodoTaxonomy:
    def test_field_registered_with_enough_entries(self):
        assert "todo" in TAXONOMIES
        assert len(TAXONOMIES["todo"]) >= 40

    def test_no_fold_duplicates(self):
        folded = [fold(v) for v in TAXONOMIES["todo"]]
        assert len(folded) == len(set(folded))

    def test_entries_are_actionable_and_trimmed(self):
        for value in TAXONOMIES["todo"]:
            assert value == value.strip()
            assert value[0].isupper(), value

    def test_canonicalizes_case_insensitively(self):
        assert canonicalize("todo", "angebot nachfassen") == "Angebot nachfassen"
        assert canonicalize("todo", "RECHNUNG STELLEN") == "Rechnung stellen"

    def test_free_text_stays_untouched(self):
        # Creatable: eigene Formulierungen bleiben erhalten
        assert canonicalize("todo", "Kaffee mit Max") == "Kaffee mit Max"
