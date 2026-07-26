"""Transparentes, reproduzierbares Scoring-Modell der Website-Analyse (rein).

Gewichtete Kategorien → Gesamtscore 0–100 → Ampel. Datenschutz führt (celox'
Kern-Verkaufsargument + rechtliches Risiko), gefolgt von messbarem Performance/SEO;
die KI-Qualitätsbewertung wiegt bewusst am wenigsten (subjektiv) und ist optional
(A2, opt-in) — fehlt sie, wird über die vorhandenen Kategorien renormiert.

Alles rein + testbar (kein IO).
"""

# Kategorie → Gewicht (Summe 100 bei allen Kategorien). Begründung: Datenschutz =
# stärkster Kaltakquise-Hook + Haftung; Performance/SEO = messbar + geschäftsrelevant;
# Technik = Basis-Hygiene; UX + KI = qualitativ/subjektiv → geringer.
CATEGORY_WEIGHTS: dict[str, int] = {
    "datenschutz": 25,
    "performance": 20,
    "seo": 20,
    "technik": 15,
    "ux": 10,
    "ki": 10,
}

CATEGORY_LABELS: dict[str, str] = {
    "datenschutz": "Datenschutz",
    "performance": "Performance",
    "seo": "SEO",
    "technik": "Technik & Sicherheit",
    "ux": "Benutzerfreundlichkeit",
    "ki": "KI-Qualitätsbewertung",
}

# Ampel-Bänder (untere Grenze inklusive).
RATING_BANDS: list[tuple[int, str]] = [(80, "gruen"), (60, "gelb"), (40, "orange"), (0, "rot")]

# Befund-Schwere → Empfehlungs-Priorität + Icon.
_SEVERITY_PRIORITY = {
    "critical": ("kritisch", "🔴", 0),
    "warning": ("hoch", "🟠", 1),
    "info": ("niedrig", "🟢", 2),
}


def rating_for(score: int) -> str:
    for lower, name in RATING_BANDS:
        if score >= lower:
            return name
    return "rot"


def overall_score(subscores: dict[str, int | None]) -> int:
    """Gewichteter Gesamtscore über die VORHANDENEN Kategorien (None = nicht
    bewertet → aus Zähler UND Nenner ausgeschlossen, Gewichte renormiert)."""
    num = 0.0
    den = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        s = subscores.get(cat)
        if s is None:
            continue
        num += max(0, min(100, s)) * weight
        den += weight
    return round(num / den) if den else 0


def build_recommendations(findings: list[dict]) -> list[dict]:
    """Befunde → nach Priorität sortierte Handlungsempfehlungen.
    Erwartet je Befund {category, issue, severity}."""
    out: list[dict] = []
    for f in findings:
        prio, icon, order = _SEVERITY_PRIORITY.get(f.get("severity", "info"),
                                                   _SEVERITY_PRIORITY["info"])
        out.append({
            "priority": prio,
            "icon": icon,
            "category": f.get("category", ""),
            "text": f.get("issue", ""),
            "_order": order,
        })
    out.sort(key=lambda r: (r["_order"], r["category"]))
    for r in out:
        r.pop("_order", None)
    return out


def _finding_key(f: dict) -> str:
    """Stabiler Schlüssel eines Befunds für den Vergleich zweier Läufe."""
    return f"{f.get('category', '')}|{f.get('issue', '')}"


def analysis_diff(current: dict, previous: dict | None) -> dict:
    """Vergleicht zwei gespeicherte Analysen (rein, testbar).

    Rückgabe: {score_delta, category_deltas: {key: delta}, new_findings: [...],
    resolved_findings: [...]} — `previous=None` ⇒ alles leer/0 (Erstanalyse)."""
    if not previous:
        return {"score_delta": 0, "category_deltas": {},
                "new_findings": [], "resolved_findings": []}

    prev_cats = {c["key"]: c.get("score", 0) for c in (previous.get("categories") or [])}
    cur_cats = {c["key"]: c.get("score", 0) for c in (current.get("categories") or [])}
    deltas = {k: cur_cats[k] - prev_cats[k] for k in cur_cats if k in prev_cats
              and cur_cats[k] != prev_cats[k]}

    cur_f = {_finding_key(f): f for f in (current.get("findings") or [])}
    prev_f = {_finding_key(f): f for f in (previous.get("findings") or [])}
    new = [f for k, f in cur_f.items() if k not in prev_f]
    resolved = [f for k, f in prev_f.items() if k not in cur_f]
    return {
        "score_delta": (current.get("overall_score") or 0) - (previous.get("overall_score") or 0),
        "category_deltas": deltas,
        "new_findings": new,
        "resolved_findings": resolved,
    }


def summarize(subscores: dict[str, int | None], findings: list[dict]) -> dict:
    """Baut das komplette Bewertungs-Summary (Gesamtscore, Ampel, kritisch-Flag,
    Kategorien mit Score+Befunden, priorisierte Empfehlungen)."""
    score = overall_score(subscores)
    has_critical = any(f.get("severity") == "critical" for f in findings)
    categories = []
    for cat, weight in CATEGORY_WEIGHTS.items():
        sub = subscores.get(cat)
        if sub is None:
            continue
        cat_findings = [f for f in findings if f.get("category_key") == cat]
        categories.append({
            "key": cat,
            "label": CATEGORY_LABELS[cat],
            "score": max(0, min(100, sub)),
            "weight": weight,
            "findings": [{"issue": f["issue"], "severity": f["severity"]} for f in cat_findings],
        })
    return {
        "overall_score": score,
        "rating": rating_for(score),
        "has_critical": has_critical,
        "categories": categories,
        "findings": [{"category": f.get("category", ""), "issue": f["issue"],
                      "severity": f["severity"]} for f in findings],
        "recommendations": build_recommendations(findings),
    }
