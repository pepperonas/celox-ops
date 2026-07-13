"""Unit-Tests für den Duplikat-Finder (netzfrei): Trigramm-Ähnlichkeit,
Clustering (exakt + fuzzy) und Konfidenz-Scoring nach Duplikat-Typ."""
from app.services.duplicate_finder import (
    REASON_COLLEAGUES,
    REASON_FIRM,
    REASON_FUZZY,
    REASON_SAME_PERSON,
    find_groups,
    score_group,
    suggest_keeper,
    trigram_similarity,
)


def _m(i, company, contact=None, **extra):
    return {"id": i, "company": company, "contact_name": contact, **extra}


# --------------------------------------------------------------------------- #
#  Trigramm-Ähnlichkeit
# --------------------------------------------------------------------------- #
def test_trigram_identical_is_one():
    assert trigram_similarity("Müller GmbH", "Müller GmbH") == 1.0


def test_trigram_similar_high_different_low():
    assert trigram_similarity("consulting bär", "consulting baer") >= 0.6
    assert trigram_similarity("apple inc", "zzz logistics") < 0.3
    assert trigram_similarity("", "x") == 0.0


# --------------------------------------------------------------------------- #
#  Scoring nach Typ
# --------------------------------------------------------------------------- #
def test_score_same_person():
    g = [_m(1, "ACME GmbH", "Max Mustermann"), _m(2, "ACME", "max mustermann")]
    score, reason = score_group(g)
    assert reason == REASON_SAME_PERSON and score >= 0.9


def test_score_firm_both_without_contact():
    g = [_m(1, "ACME GmbH"), _m(2, "acme gmbh ")]
    score, reason = score_group(g)
    assert reason == REASON_FIRM and score >= 0.7


def test_score_colleagues_low_and_not_preselected():
    g = [_m(1, "Deutsche Bank", "Anna A"), _m(2, "Deutsche Bank AG", "Bernd B")]
    score, reason = score_group(g)
    assert reason == REASON_COLLEAGUES and score <= 0.35


def test_score_fuzzy_penalty_when_names_not_exact():
    # Verschiedene Ansprechpartner + nur fuzzy-ähnlicher Firmenname → fuzzy-Reason
    g = [_m(1, "consulting bär", "Anna"), _m(2, "consulting baer", "Bernd")]
    score, reason = score_group(g)
    assert reason == REASON_FUZZY


# --------------------------------------------------------------------------- #
#  Clustering
# --------------------------------------------------------------------------- #
def test_exact_normalized_company_groups():
    leads = [_m(1, "Müller GmbH", "A"), _m(2, "müller gmbh ", "A"), _m(3, "Andere AG", "B")]
    groups = find_groups(leads, fuzzy=False)
    assert len(groups) == 1
    assert {m["id"] for m in groups[0]["members"]} == {1, 2}


def test_fuzzy_links_similar_names():
    leads = [_m(1, "Consulting Bär", "A"), _m(2, "Consulting Baer", "A")]
    groups = find_groups(leads, fuzzy=True)
    assert len(groups) == 1 and len(groups[0]["members"]) == 2


def test_distinct_companies_stay_separate():
    leads = [_m(1, "Apple Inc"), _m(2, "Microsoft GmbH"), _m(3, "Tesla")]
    assert find_groups(leads) == []


def test_singletons_excluded():
    assert find_groups([_m(1, "Solo GmbH", "X")]) == []


def test_groups_sorted_by_confidence():
    leads = [
        _m(1, "Kollege AG", "Anna"), _m(2, "Kollege AG", "Bernd"),      # colleagues (niedrig)
        _m(3, "DoppelPerson GmbH", "Max M"), _m(4, "DoppelPerson", "max m"),  # same person (hoch)
    ]
    groups = find_groups(leads)
    assert len(groups) == 2
    assert groups[0]["reason"] == REASON_SAME_PERSON     # höchste Konfidenz zuerst
    assert groups[1]["reason"] == REASON_COLLEAGUES


def test_suggest_keeper_prefers_most_activities():
    members = [
        _m(1, "X", "A", activity_count=0, created_at="2026-01-01"),
        _m(2, "X", "A", activity_count=5, created_at="2026-02-01"),
    ]
    assert suggest_keeper(members) == "2"
