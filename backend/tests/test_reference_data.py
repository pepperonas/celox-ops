"""DB-freie Tests für die reinen Referenzdaten-Helfer + Registry (Phase B2)."""
from app.services.reference_data import (
    FIELD_LABELS,
    FIELD_STORES,
    MANAGED_FIELDS,
    remove_from_list,
    rename_in_list,
)
from app.services.taxonomy import TAXONOMIES


# ---- rename_in_list --------------------------------------------------------
def test_rename_replaces_and_reports_change():
    out, changed = rename_in_list(["Alt", "Behalten"], "alt", "Neu")
    assert out == ["Neu", "Behalten"] and changed


def test_rename_dedupes_when_target_exists():
    out, changed = rename_in_list(["B", "A"], "a", "B")   # A→B, B schon da
    assert out == ["B"] and changed


def test_rename_dedupes_target_before_source():
    out, changed = rename_in_list(["A", "B"], "a", "B")
    assert out == ["B"] and changed


def test_rename_no_match_is_unchanged():
    out, changed = rename_in_list(["X", "Y"], "a", "Neu")
    assert out == ["X", "Y"] and not changed


def test_rename_is_fold_insensitive():
    # bestehender Wert in Kleinschreibung wird auf die kanonische Form gezogen
    out, changed = rename_in_list(["hausverwaltung"], "hausverwaltung", "Hausverwaltung")
    assert out == ["Hausverwaltung"] and changed


def test_rename_handles_none_and_empty():
    assert rename_in_list(None, "a", "B") == ([], False)
    assert rename_in_list([], "a", "B") == ([], False)


# ---- remove_from_list ------------------------------------------------------
def test_remove_drops_matching_fold():
    out, changed = remove_from_list(["Tag", "Weg"], "weg")
    assert out == ["Tag"] and changed


def test_remove_no_match_unchanged():
    out, changed = remove_from_list(["A"], "b")
    assert out == ["A"] and not changed


def test_remove_handles_none():
    assert remove_from_list(None, "x") == ([], False)


# ---- Registry-Integrität ---------------------------------------------------
def test_managed_fields_have_labels():
    assert set(MANAGED_FIELDS) == set(FIELD_LABELS)


def test_managed_fields_are_known_taxonomies_or_stores():
    for f in MANAGED_FIELDS:
        assert f in TAXONOMIES, f  # jedes verwaltbare Feld hat eine Taxonomie


def test_stores_have_valid_kind():
    for f, store in FIELD_STORES.items():
        assert store.kind in ("scalar", "array")
        assert hasattr(store.model, store.column), f"{f}: {store.column} fehlt am Modell"


def test_zielsystem_is_managed_but_has_no_record_store():
    # rein kuratiert/eigene Werte, keine Record-Propagation
    assert "zielsystem" in MANAGED_FIELDS
    assert "zielsystem" not in FIELD_STORES
