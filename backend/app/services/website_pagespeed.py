"""Google PageSpeed Insights für die Website-Analyse (A2, opt-in).

`parse_pagespeed` ist rein (nimmt die API-Antwort) und damit testbar; `fetch_pagespeed`
macht den HTTP-Call. Liefert Lighthouse-Kategoriescores (0–100) + Core Web Vitals.
Bewusst opt-in: der Call dauert ~10–30 s und zählt auf die Google-Quota.
"""
import httpx

from app.config import settings

PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

_CATEGORY_KEYS = {
    "performance": "Performance",
    "accessibility": "Barrierefreiheit",
    "best-practices": "Best Practices",
    "seo": "SEO",
}
# Core Web Vitals + ergänzende Metriken (Lighthouse-Audit-IDs).
_METRIC_KEYS = {
    "largest-contentful-paint": "LCP (Largest Contentful Paint)",
    "cumulative-layout-shift": "CLS (Cumulative Layout Shift)",
    "total-blocking-time": "TBT (Total Blocking Time)",
    "first-contentful-paint": "FCP (First Contentful Paint)",
    "speed-index": "Speed Index",
}


def parse_pagespeed(data: dict) -> dict:
    """Lighthouse-Antwort → {scores: {key: 0-100}, metrics: [{label, value, score}]}.
    Fehlende Kategorien werden weggelassen (nicht als 0 gewertet)."""
    lhr = data.get("lighthouseResult") or {}
    cats = lhr.get("categories") or {}
    audits = lhr.get("audits") or {}

    scores: dict[str, int] = {}
    for key in _CATEGORY_KEYS:
        raw = (cats.get(key) or {}).get("score")
        if raw is not None:
            scores[key] = int(round(float(raw) * 100))

    metrics = []
    for key, label in _METRIC_KEYS.items():
        audit = audits.get(key) or {}
        if not audit:
            continue
        s = audit.get("score")
        metrics.append({
            "label": label,
            "value": audit.get("displayValue") or "–",
            "score": int(round(float(s) * 100)) if s is not None else None,
        })
    return {"scores": scores, "metrics": metrics,
            "strategy": (lhr.get("configSettings") or {}).get("formFactor")}


async def fetch_pagespeed(url: str, strategy: str = "mobile") -> dict | None:
    """Holt die PageSpeed-Analyse. Rückgabe None bei Fehler/Timeout (die
    Gesamtanalyse soll nie an PageSpeed scheitern)."""
    params: dict = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "accessibility", "best-practices", "seo"],
    }
    if settings.PAGESPEED_API_KEY:
        params["key"] = settings.PAGESPEED_API_KEY
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(PAGESPEED_API, params=params)
        if resp.status_code != 200:
            return None
        return parse_pagespeed(resp.json())
    except (httpx.HTTPError, ValueError):
        return None
