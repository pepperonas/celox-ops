"""DB-freie Tests für das Website-Scoring-Modell (rein)."""
from app.services.website_scoring import (
    CATEGORY_WEIGHTS,
    build_recommendations,
    overall_score,
    rating_for,
    summarize,
)


def test_weights_sum_to_100():
    assert sum(CATEGORY_WEIGHTS.values()) == 100


def test_rating_bands():
    assert rating_for(100) == "gruen"
    assert rating_for(80) == "gruen"
    assert rating_for(79) == "gelb"
    assert rating_for(60) == "gelb"
    assert rating_for(59) == "orange"
    assert rating_for(40) == "orange"
    assert rating_for(39) == "rot"
    assert rating_for(0) == "rot"


def test_overall_all_perfect_is_100():
    subs = {k: 100 for k in CATEGORY_WEIGHTS}
    assert overall_score(subs) == 100


def test_overall_weighted_datenschutz_dominates():
    # Datenschutz (25%) auf 0, Rest 100 → deutlich unter 100, aber > 70
    subs = {k: 100 for k in CATEGORY_WEIGHTS}
    subs["datenschutz"] = 0
    assert overall_score(subs) == 75  # (100*75)/100


def test_overall_renormalizes_over_present_categories():
    # KI fehlt (None) → über die restlichen 90 Gewichtspunkte renormiert
    subs = {"datenschutz": 100, "performance": 100, "seo": 100,
            "technik": 100, "ux": 100, "ki": None}
    assert overall_score(subs) == 100
    subs["datenschutz"] = 0
    # (0*25 + 100*65)/90 = 72.2 → 72
    assert overall_score(subs) == 72


def test_overall_empty_is_zero():
    assert overall_score({k: None for k in CATEGORY_WEIGHTS}) == 0


def test_recommendations_sorted_by_priority():
    findings = [
        {"category": "SEO", "issue": "b", "severity": "info"},
        {"category": "Datenschutz", "issue": "a", "severity": "critical"},
        {"category": "Performance", "issue": "c", "severity": "warning"},
    ]
    recs = build_recommendations(findings)
    assert [r["priority"] for r in recs] == ["kritisch", "hoch", "niedrig"]
    assert recs[0]["icon"] == "🔴"
    assert "_order" not in recs[0]


def test_summarize_flags_critical_and_builds_categories():
    subs = {"datenschutz": 20, "performance": 100, "seo": 100, "technik": 100,
            "ux": 100, "ki": None}
    findings = [
        {"category_key": "datenschutz", "category": "Datenschutz",
         "issue": "Keine Datenschutzerklärung", "severity": "critical"},
    ]
    out = summarize(subs, findings)
    assert out["has_critical"] is True
    assert out["rating"] == rating_for(out["overall_score"])
    ds = next(c for c in out["categories"] if c["key"] == "datenschutz")
    assert ds["score"] == 20 and ds["weight"] == 25 and len(ds["findings"]) == 1
    # KI (None) taucht nicht als Kategorie auf
    assert all(c["key"] != "ki" for c in out["categories"])
    assert out["findings"][0]["severity"] == "critical"
