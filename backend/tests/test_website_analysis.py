"""DB-freie Tests für die reine technische Website-Analyse (analyze_html) + SSRF-Guard."""
from app.services.website_analysis import _host_is_public, _sanitize_url, analyze_html

_GOOD = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beispiel GmbH — Softwareentwicklung</title>
<meta name="description" content="Wir entwickeln individuelle Software fuer den Mittelstand und begleiten Projekte von der Idee bis zum Betrieb.">
<meta property="og:title" content="Beispiel GmbH"><meta property="og:image" content="/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://beispiel.de/">
<link rel="icon" href="/favicon.ico">
<script type="application/ld+json">{"@type":"Organization"}</script></head>
<body><h1>Willkommen</h1><h2>Leistungen</h2>
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
    assert "Google Fonts (extern)" in r["technologies"]
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


# ---- SSRF-Guard (rein, IP-Literale → kein Netzwerk) ------------------------
def test_host_is_public_blocks_internal_ranges():
    for internal in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "172.16.0.1",
                     "169.254.169.254", "::1", "0.0.0.0"):
        assert _host_is_public(internal) is False, internal


def test_host_is_public_allows_public_ip():
    assert _host_is_public("8.8.8.8") is True
    assert _host_is_public("1.1.1.1") is True


def test_host_is_public_empty_is_false():
    assert _host_is_public("") is False


def test_sanitize_url_enforces_scheme_and_defaults_https():
    assert _sanitize_url("example.com") == "https://example.com/"
    assert _sanitize_url("http://example.com/path?q=1") == "http://example.com/path?q=1"


def test_sanitize_url_strips_userinfo_and_lowercases_host():
    assert _sanitize_url("https://user:pass@Example.COM/x") == "https://example.com/x"


def test_sanitize_url_rejects_non_http_schemes():
    assert _sanitize_url("ftp://example.com") is None
    assert _sanitize_url("file:///etc/passwd") is None
    assert _sanitize_url("") is None


# ---- Erweiterte Signale (Phase 1) ------------------------------------------
def test_good_site_has_og_and_structured_data_signals():
    r = analyze_html("https", _GOOD, _headers(), 600, 50_000, final_url="https://beispiel.de/")
    sig = r["signals"]
    assert sig["meta"]["og_present"] is True
    assert sig["meta"]["twitter_present"] is True
    assert sig["meta"]["canonical"] is True
    assert sig["meta"]["favicon"] is True
    assert sig["meta"]["lang"] == "de"
    assert sig["seo"]["headings"]["h1"] == 1 and sig["seo"]["headings"]["h2"] == 1
    assert "Organization" in sig["seo"]["structured_data"]


def test_noindex_is_critical_seo_finding():
    html = _GOOD.replace("<head>", '<head><meta name="robots" content="noindex,nofollow">')
    r = analyze_html("https", html, _headers(), 600, 50_000, final_url="https://x.de/")
    assert r["signals"]["meta"]["noindex"] is True
    assert any(f["severity"] == "critical" and "noindex" in f["issue"] for f in r["findings"])


def test_missing_sitemap_and_broken_links_from_extras():
    r = analyze_html("https", _GOOD, _headers(), 600, 50_000, final_url="https://x.de/",
                     extras={"robots_txt": False, "sitemap": False,
                             "broken_links": ["404 https://x.de/alt"], "links_checked": 10})
    issues = " ".join(f["issue"] for f in r["findings"])
    assert "robots.txt" in issues and "sitemap.xml" in issues and "defekte interne Links" in issues


def test_server_and_powered_by_headers_are_flagged():
    r = analyze_html("https", _GOOD, _headers(server="Apache/2.4.41", **{"x-powered-by": "PHP/7.4"}),
                     600, 50_000, final_url="https://x.de/")
    issues = " ".join(f["issue"] for f in r["findings"])
    assert "X-Powered-By" in issues and "Server-Header" in issues
    assert r["signals"]["tech"]["server"] == "apache/2.4.41"
