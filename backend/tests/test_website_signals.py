"""DB-freie Tests für den Signal-Extraktor (rein, ohne Netzwerk)."""
from app.services.website_signals import (
    detect_trackers,
    extract_signals,
    link_stats,
)

_HTML = """<!doctype html><html lang="de-DE"><head><meta charset="UTF-8">
<title>Muster GmbH – Elektroinstallation Berlin</title>
<meta name="description" content="Ihr Elektriker in Berlin.">
<meta name="robots" content="index,follow">
<meta property="og:title" content="Muster GmbH"><meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="viewport" content="width=device-width">
<link rel="canonical" href="https://muster.de/"><link rel="apple-touch-icon" href="/i.png">
<script src="/wp-content/themes/x/jquery.min.js"></script>
<script src="https://www.googletagmanager.com/gtm.js"></script>
<script src="https://snap.licdn.com/li.lms-analytics/insight.min.js"></script>
<script src="https://www.clarity.ms/tag/abc"></script>
<link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet">
<script type="application/ld+json">{"@type":"LocalBusiness"}</script></head>
<body><h1>Elektro</h1><h2>Leistungen</h2><h2>Kontakt</h2><h3>Anfahrt</h3>
<a href="/impressum">Impressum</a><a href="/datenschutz">Datenschutz</a>
<a href="https://partner.example.com">Partner</a>
<img src="a.jpg" alt="Team"><img src="b.jpg">
<div class="cookie-consent">Wir nutzen Cookies — bitte zustimmen</div>
</body></html>"""

_HEADERS = {"server": "nginx/1.18.0", "x-powered-by": "PHP/8.1", "cf-ray": "abc123"}


def _sig():
    return extract_signals("https://muster.de/", _HTML, _HEADERS)


# ---- Meta ------------------------------------------------------------------
def test_meta_basics():
    m = _sig()["meta"]
    assert m["title"].startswith("Muster GmbH")
    assert m["description"] == "Ihr Elektriker in Berlin."
    assert m["canonical"] is True and m["favicon"] is True and m["viewport"] is True
    assert m["lang"] == "de-DE" and m["charset"].lower() == "utf-8"
    assert m["noindex"] is False


def test_opengraph_and_twitter_detected():
    m = _sig()["meta"]
    assert m["og_present"] is True and m["og"]["title"] == "Muster GmbH"
    assert m["twitter_present"] is True and m["twitter_card"] == "summary"


def test_noindex_detected():
    html = _HTML.replace('content="index,follow"', 'content="noindex, nofollow"')
    assert extract_signals("https://x.de/", html, {})["meta"]["noindex"] is True


# ---- SEO -------------------------------------------------------------------
def test_heading_structure_and_images():
    seo = _sig()["seo"]
    assert seo["headings"] == {"h1": 1, "h2": 2, "h3": 1, "h4": 0, "h5": 0, "h6": 0}
    assert seo["images_total"] == 2 and seo["images_without_alt"] == 1


def test_structured_data_types():
    assert _sig()["seo"]["structured_data"] == ["LocalBusiness"]


def test_link_stats_splits_internal_external():
    ls = link_stats(_HTML, "https://muster.de/")
    assert ls["external_count"] == 1
    assert any(u.endswith("/impressum") for u in ls["internal"])


def test_link_stats_ignores_mailto_and_tel():
    ls = link_stats('<a href="mailto:a@b.de">M</a><a href="tel:+49">T</a><a href="/x">X</a>',
                    "https://muster.de/")
    assert ls["internal_count"] == 1 and ls["external_count"] == 0


# ---- Technik ---------------------------------------------------------------
def test_cms_framework_and_cdn_detection():
    t = _sig()["tech"]
    assert "WordPress" in t["cms"]
    assert "jQuery" in t["frameworks"]
    assert "Cloudflare" in t["cdn"]
    assert t["server"] == "nginx/1.18.0" and t["powered_by"] == "PHP/8.1"
    assert t["https"] is True


# ---- Datenschutz -----------------------------------------------------------
def test_extended_tracker_detection():
    names = [t["name"] for t in _sig()["privacy"]["trackers"]]
    assert "Google Tag Manager" in names
    assert "LinkedIn Insight Tag" in names
    assert "Microsoft Clarity" in names
    assert "Google Fonts (extern)" in names


def test_high_risk_trackers_listed_first():
    trackers = detect_trackers("clarity.ms matomo.js youtube.com/embed")
    assert trackers[0]["risk"] == "high"
    assert trackers[-1]["risk"] == "low"


def test_privacy_flags_and_cookie_banner():
    p = _sig()["privacy"]
    assert p["has_impressum"] is True and p["has_privacy"] is True
    assert p["has_cookie_banner"] is True
    assert p["google_fonts_external"] is True
    assert "Microsoft Clarity" in p["high_risk_trackers"]


def test_cmp_detection_by_name():
    sig = extract_signals("https://x.de/", '<script src="https://consent.cookiebot.com/uc.js">', {})
    assert sig["privacy"]["cmps"] == ["Cookiebot"]
    assert sig["privacy"]["has_cookie_banner"] is True


def test_empty_html_is_safe():
    sig = extract_signals("https://x.de/", "", {})
    assert sig["meta"]["title"] == "" and sig["seo"]["images_total"] == 0
    assert sig["privacy"]["trackers"] == [] and sig["tech"]["cms"] == []
