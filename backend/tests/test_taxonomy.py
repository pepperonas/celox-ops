"""DB-freie Tests: Taxonomie-Integrität, Normalisierung, Merge-Ranking, Migration."""
from types import SimpleNamespace

from app.scripts.normalize_taxonomy_values import plan_lead_changes
from app.services.taxonomy import (
    SYNONYMS,
    TAXONOMIES,
    canonicalize,
    fold,
    merge_suggestions,
)


# ---- Integrität ------------------------------------------------------------
def test_taxonomies_are_substantial_and_deduped():
    for field, values in TAXONOMIES.items():
        assert len(values) >= 20, f"{field}: nur {len(values)} Einträge"
        folded = [fold(v) for v in values]
        assert len(set(folded)) == len(folded), f"{field}: fold-Dubletten"
        assert all(v.strip() == v and v for v in values), f"{field}: Whitespace/leer"


def test_synonyms_point_to_existing_canonical_values():
    all_canonical = {fold(v) for values in TAXONOMIES.values() for v in values}
    for syn, canon in SYNONYMS.items():
        assert fold(canon) in all_canonical, f"Synonym '{syn}' → '{canon}' fehlt in TAXONOMIES"


# ---- fold / canonicalize -----------------------------------------------------
def test_fold_trims_lowercases_and_strips_diacritics():
    assert fold("  Geschäftsführung  ") == "geschaftsfuhrung"
    assert fold("Café") == "cafe"
    assert fold("") == ""


def test_canonicalize_synonym_case_and_unknown():
    assert canonicalize("role", "GF") == "Geschäftsführung"
    assert canonicalize("role", "ceo") == "Geschäftsführung"
    assert canonicalize("tag", "DSVGO") == "DSGVO"                    # Tippfehler
    assert canonicalize("tag", "hausverwaltung") == "Hausverwaltung"  # Case-Variante
    assert canonicalize("source", "linked in") == "LinkedIn"
    # creatable: Unbekanntes bleibt (getrimmt) erhalten
    assert canonicalize("role", "  Hofnarr  ") == "Hofnarr"
    assert canonicalize("role", "") == ""


# ---- merge_suggestions -------------------------------------------------------
def test_merge_ranks_own_values_first_then_alphabetical():
    out = merge_suggestions("source", {"KI-Recherche": 71, "Recherche": 10})
    assert out[0] == "KI-Recherche"
    assert out[1] == "Recherche"
    rest = out[2:]
    assert rest == sorted(rest, key=str.lower)


def test_merge_dedupes_own_variants_into_canonical():
    out = merge_suggestions("tag", {"hausverwaltung": 3, "Hausverwaltung": 2, "DSVGO": 1})
    assert out[0] == "Hausverwaltung"          # 3+2=5 gemergt, kuratierte Schreibweise
    assert "hausverwaltung" not in out
    assert "DSVGO" not in out and "DSGVO" in out


def test_merge_keeps_unknown_own_values_and_filters_by_q():
    out = merge_suggestions("vendor", {"Mein Spezial-Shop": 4})
    assert "Mein Spezial-Shop" in out
    filtered = merge_suggestions("vendor", {}, q="hetz")
    assert filtered == ["Hetzner"]


def test_merge_respects_limit():
    assert len(merge_suggestions("branche", {}, limit=5)) == 5


# ---- Migration (plan_lead_changes) -------------------------------------------
def _lead(company="X", role=None, source=None, tags=None):
    return SimpleNamespace(company=company, role=role, source=source, tags=tags)


def test_plan_normalizes_role_source_and_dedupes_tags():
    leads = [
        _lead(role="GF", source="linked in", tags=["hausverwaltung", "Hausverwaltung", "DSVGO"]),
        _lead(role="Geschäftsführung", tags=["DSGVO"]),  # bereits kanonisch → kein Change
    ]
    changes = plan_lead_changes(leads)
    assert len(changes) == 1
    _, patch = changes[0]
    assert patch["role"] == ("GF", "Geschäftsführung")
    assert patch["source"] == ("linked in", "LinkedIn")
    assert patch["tags"][1] == ["Hausverwaltung", "DSGVO"]


def test_plan_empty_and_none_fields_untouched():
    assert plan_lead_changes([_lead(), _lead(tags=[])]) == []
