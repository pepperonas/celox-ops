"""DB-freie Tests für die reine technische Website-Analyse (analyze_html)."""
from app.services.website_analysis import analyze_html

_GOOD = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beispiel GmbH — Softwareentwicklung</title>
<meta name="description" content="Wir bauen Software.">
<link rel="canonical" href="https://beispiel.de/">
<link rel="icon" href="/favicon.ico">
<script type="application/ld+json">{}</script></head>
<body><h1>Willkommen</h1>
<a href="/impressum">Impressum</a><a href="/datenschutz">Datenschutz</a>
<img src="a.jpg" alt="x"></body></html>"""

_BAD = """<html><head></head><body>
<img src="a.jpg"><script src="https://www.google-analytics.com/ga.js"></script>
<link href="https://fonts.googleapis.com/css?family=Roboto"></body></html>"""


def _headers(**h):
    return {k.lower(): v.lower() for k, v in h.items()}


def test_good_site_scores_high_and_no_critical():
    r = analyze_html("https", _GOOD.lower(),
                     _headers(**{"content-security-policy": "x", "x-frame-options": "deny",
                                 "strict-transport-security": "max-age=1"}),
                     load_time_ms=600, content_length=50_000)
    assert r["subscores"]["datenschutz"] >= 90
    assert r["subscores"]["seo"] >= 90
    assert r["subscores"]["technik"] >= 90
    assert not any(f["severity"] == "critical" for f in r["findings"])


def test_missing_impressum_and_privacy_are_critical():
    r = analyze_html("https", _BAD.lower(), _headers(), 800, 20_000)
    issues = " ".join(f["issue"] for f in r["findings"])
    assert "Impressum" in issues
    assert "Datenschutzerklärung" in issues
    crit = [f for f in r["findings"] if f["severity"] == "critical"]
    assert any("Impressum" in f["issue"] for f in crit)


def test_trackers_without_banner_flagged_and_detected():
    r = analyze_html("https", _BAD.lower(), _headers(), 800, 20_000)
    assert "Google Analytics" in r["technologies"]
    assert "Google Fonts" in r["technologies"]
    assert any("Cookie-Banner" in f["issue"] for f in r["findings"])
    assert any("Google Fonts" in f["issue"] for f in r["findings"])


def test_no_https_is_critical_technik():
    r = analyze_html("http", _GOOD.lower(), _headers(), 500, 40_000)
    assert any(f["severity"] == "critical" and "HTTPS" in f["issue"] for f in r["findings"])
    assert r["subscores"]["technik"] < 70


def test_slow_load_deducts_performance():
    fast = analyze_html("https", _GOOD.lower(), _headers(), 500, 40_000)["subscores"]["performance"]
    slow = analyze_html("https", _GOOD.lower(), _headers(), 6000, 40_000)["subscores"]["performance"]
    assert slow < fast
    assert slow <= 60


def test_images_without_alt_hits_ux():
    r = analyze_html("https", _BAD.lower(), _headers(), 800, 20_000)
    assert any("Alt-Text" in f["issue"] for f in r["findings"])
    assert r["subscores"]["ux"] < 100


def test_meta_reports_flags():
    r = analyze_html("https", _GOOD.lower(), _headers(), 600, 50_000)
    assert r["meta"]["has_impressum"] is True
    assert r["meta"]["has_privacy"] is True
