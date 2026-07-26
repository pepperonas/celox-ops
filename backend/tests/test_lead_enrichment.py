"""DB-/netzfreie Tests für die leichte Kandidaten-Anreicherung."""
from app.services.lead_enrichment import (
    contact_page_url,
    enrichment_from_html,
    enrichment_notes,
    extract_emails,
    extract_socials,
    merge_enrichment,
    pick_email,
    privacy_hint,
    privacy_rating,
)

_HTML = """<!doctype html><html lang="de"><head>
<title>Muster Elektro GmbH</title>
<meta name="description" content="Elektroinstallation und Smart Home in Berlin seit 1998.">
<meta name="generator" content="WordPress 6.5">
<script src="https://www.googletagmanager.com/gtm.js"></script></head>
<body>
<a href="https://www.linkedin.com/company/muster-elektro/">LinkedIn</a>
<a href="https://www.facebook.com/sharer.php?u=https://muster.de">teilen</a>
<a href="https://www.facebook.com/musterelektro">Facebook</a>
<a href="https://www.instagram.com/muster.elektro/">Insta</a>
<a href="/impressum">Impressum</a><a href="/datenschutz">Datenschutz</a>
<a href="mailto:info@muster-elektro.de">Mail</a>
<p>Chef: max.mueller@muster-elektro.de · noreply@muster-elektro.de</p>
</body></html>"""


# ---- Social-Profile --------------------------------------------------------
def test_socials_extracted_per_network():
    s = extract_socials(_HTML)
    assert s["linkedin"].endswith("/company/muster-elektro")
    assert s["instagram"].endswith("/muster.elektro")


def test_share_buttons_are_not_profiles():
    s = extract_socials(_HTML)
    # Der Share-Link darf nicht als Facebook-Profil zählen — das echte gewinnt
    # (Profil-URLs werden auf die kanonische Form ohne www normalisiert).
    assert s["facebook"] == "https://facebook.com/musterelektro"


def test_socials_empty_without_links():
    assert extract_socials("<html><body>nichts</body></html>") == {}


# ---- E-Mail ----------------------------------------------------------------
def test_emails_extracted_and_technical_ones_dropped():
    mails = extract_emails(_HTML)
    assert "info@muster-elektro.de" in mails
    assert "max.mueller@muster-elektro.de" in mails
    assert not any("noreply" in m for m in mails)


def test_pick_email_prefers_general_mailbox():
    assert pick_email(["max.mueller@x.de", "info@x.de"]) == "info@x.de"
    assert pick_email(["a.b@x.de"]) == "a.b@x.de"
    assert pick_email([]) is None


# ---- Datenschutz-Ampel -----------------------------------------------------
def test_privacy_rating_red_without_impressum():
    assert privacy_rating({"has_impressum": False, "has_privacy": True}) == "rot"
    assert privacy_hint({"has_impressum": False}) == "kein Impressum gefunden"


def test_privacy_rating_red_for_high_risk_tracker_without_banner():
    p = {"has_impressum": True, "has_privacy": True, "has_cookie_banner": False,
         "high_risk_trackers": ["Google Analytics"], "trackers": [{"name": "Google Analytics"}]}
    assert privacy_rating(p) == "rot"
    assert privacy_hint(p) == "Google Analytics ohne Cookie-Banner"


def test_privacy_rating_yellow_with_banner_and_green_when_clean():
    p = {"has_impressum": True, "has_privacy": True, "has_cookie_banner": True,
         "high_risk_trackers": ["Google Analytics"], "trackers": [{"name": "Google Analytics"}]}
    assert privacy_rating(p) == "gelb"
    assert privacy_rating({"has_impressum": True, "has_privacy": True}) == "gruen"


# ---- Zusammenbau -----------------------------------------------------------
def test_enrichment_from_html_collects_all_fields():
    e = enrichment_from_html("https://muster.de/", _HTML, {"server": "nginx"})
    assert e["description"].startswith("Elektroinstallation")
    assert "WordPress" in e["technologies"]
    assert e["socials"]["linkedin"]
    assert e["privacy_rating"] == "rot"          # GTM ohne Banner
    assert "info@muster-elektro.de" in e["emails"]
    assert e["enriched"] is True


def test_description_falls_back_to_title():
    html = "<html><head><title>Meier Dachdecker</title></head><body></body></html>"
    assert enrichment_from_html("https://x.de/", html, {})["description"] == "Meier Dachdecker"


def test_merge_never_overwrites_source_data():
    row = {"name": "Muster", "email": "kontakt@quelle.de", "website": "https://muster.de"}
    merged = merge_enrichment(row, enrichment_from_html("https://muster.de/", _HTML, {}))
    assert merged["email"] == "kontakt@quelle.de"      # Quelle gewinnt
    assert merged["description"]


def test_merge_fills_missing_email():
    merged = merge_enrichment({"name": "M", "email": None},
                              enrichment_from_html("https://muster.de/", _HTML, {}))
    assert merged["email"] == "info@muster-elektro.de"


def test_contact_page_url_is_same_host_only():
    assert contact_page_url(_HTML, "https://muster.de/") == "https://muster.de/impressum"
    foreign = '<a href="https://andere.de/impressum">I</a>'
    assert contact_page_url(foreign, "https://muster.de/") is None


def test_notes_contain_only_present_facts():
    row = merge_enrichment({"name": "M"}, enrichment_from_html("https://muster.de/", _HTML, {}))
    lines = enrichment_notes(row)
    assert any(line.startswith("Elektroinstallation") for line in lines)
    assert any(line.startswith("Technik:") for line in lines)
    assert any(line.startswith("LinkedIn:") for line in lines)
    assert enrichment_notes({"name": "leer"}) == []
