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


# ---- analysis_diff (rein) ---------------------------------------------------
def _analysis(score, cats, findings):
    return {"overall_score": score,
            "categories": [{"key": k, "score": v} for k, v in cats.items()],
            "findings": findings}


def test_diff_without_previous_is_empty():
    from app.services.website_scoring import analysis_diff
    d = analysis_diff(_analysis(80, {"seo": 90}, []), None)
    assert d == {"score_delta": 0, "category_deltas": {},
                 "new_findings": [], "resolved_findings": []}


def test_diff_reports_score_and_category_deltas():
    from app.services.website_scoring import analysis_diff
    cur = _analysis(84, {"seo": 100, "technik": 60}, [])
    prev = _analysis(92, {"seo": 100, "technik": 80}, [])
    d = analysis_diff(cur, prev)
    assert d["score_delta"] == -8
    assert d["category_deltas"] == {"technik": -20}   # unveraenderte Kategorie fehlt


def test_diff_lists_new_and_resolved_findings():
    from app.services.website_scoring import analysis_diff
    f_old = {"category": "SEO", "issue": "Keine Meta-Description", "severity": "warning"}
    f_new = {"category": "Datenschutz", "issue": "Kein Cookie-Banner", "severity": "critical"}
    f_keep = {"category": "UX", "issue": "Kein Favicon", "severity": "info"}
    d = analysis_diff(_analysis(70, {}, [f_new, f_keep]), _analysis(70, {}, [f_old, f_keep]))
    assert [f["issue"] for f in d["new_findings"]] == ["Kein Cookie-Banner"]
    assert [f["issue"] for f in d["resolved_findings"]] == ["Keine Meta-Description"]


def test_diff_handles_new_category_gracefully():
    from app.services.website_scoring import analysis_diff
    # KI kam erst mit der Tiefenanalyse dazu -> kein Delta (kein Vorwert)
    d = analysis_diff(_analysis(80, {"seo": 90, "ki": 70}, []), _analysis(80, {"seo": 90}, []))
    assert d["category_deltas"] == {}
