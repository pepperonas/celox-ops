"""Zentraler Signal-Extraktor für die Website-Analyse (rein, ohne IO).

Trennt **Fakten** (was steht auf der Seite / in den Headern?) von der **Bewertung**
(`website_analysis.analyze_html` erzeugt daraus Befunde + Subscores) und der
**Darstellung**. Neue Signale kommen hier dazu — Scoring und UI ziehen nach, ohne
dass am Fetch-Pfad etwas geändert werden muss.

Alle Erkennungen sind Heuristiken auf dem HTML der Startseite; sie sind bewusst
konservativ (lieber „nicht erkannt" als falsch behauptet).
"""
import re
from urllib.parse import urljoin, urlsplit

# --------------------------------------------------------------------------- #
#  Erkennungs-Tabellen
# --------------------------------------------------------------------------- #
# Consent-Management-Plattformen.
CMP_SIGNATURES: dict[str, tuple[str, ...]] = {
    "Cookiebot": ("cookiebot",),
    "Usercentrics": ("usercentrics",),
    "Borlabs Cookie": ("borlabs",),
    "Complianz": ("complianz",),
    "Klaro": ("klaro",),
    "OneTrust": ("onetrust", "optanon"),
    "CookieFirst": ("cookiefirst",),
    "consentmanager": ("consentmanager",),
    "Cookie Notice / CookieConsent": ("cookieconsent", "cookie-consent", "cookie-notice"),
    "Iubenda": ("iubenda",),
}

# Externe Dienste mit Datenschutz-Relevanz → (Signaturen, Risiko).
# risk: 'high' = personenbezogene Übermittlung/Tracking ohne Einwilligung heikel,
#       'medium' = Einbettung Dritter, 'low' = i. d. R. unkritisch/anonym.
TRACKER_SIGNATURES: dict[str, tuple[tuple[str, ...], str]] = {
    "Google Analytics": (("google-analytics.com", "googletagmanager.com/gtag", "gtag(", "ga('create'"), "high"),
    "Google Tag Manager": (("googletagmanager.com/gtm", "datalayer.push"), "high"),
    "Google Ads / DoubleClick": (("doubleclick.net", "googleadservices.com", "googlesyndication.com"), "high"),
    "Meta / Facebook Pixel": (("connect.facebook.net", "fbevents.js", "fbq("), "high"),
    "LinkedIn Insight Tag": (("snap.licdn.com", "_linkedin_partner_id", "linkedin_data_partner"), "high"),
    "TikTok Pixel": (("analytics.tiktok.com", "ttq.load", "ttq.page"), "high"),
    "Microsoft Clarity": (("clarity.ms",), "high"),
    "Hotjar": (("hotjar.com", "hjsv"), "high"),
    "Pinterest Tag": (("pintrk(", "s.pinimg.com/ct"), "high"),
    "X / Twitter Pixel": (("static.ads-twitter.com", "twq("), "high"),
    "HubSpot": (("js.hs-scripts.com", "hs-analytics"), "high"),
    "Intercom": (("widget.intercom.io", "intercomsettings"), "medium"),
    "Google Fonts (extern)": (("fonts.googleapis.com", "fonts.gstatic.com"), "high"),
    "Google Maps": (("maps.googleapis.com", "google.com/maps/embed", "maps.google.com/maps"), "medium"),
    "YouTube-Einbettung": (("youtube.com/embed", "youtube-nocookie.com", "youtu.be/"), "medium"),
    "Vimeo-Einbettung": (("player.vimeo.com",), "medium"),
    "reCAPTCHA": (("recaptcha", "gstatic.com/recaptcha"), "medium"),
    "Matomo / Piwik": (("matomo.js", "piwik.js", "matomo.php"), "low"),
    "Plausible": (("plausible.io",), "low"),
    "Fathom": (("cdn.usefathom.com",), "low"),
    "etracker": (("etracker.com",), "low"),
}

# CMS / Shop-Systeme.
CMS_SIGNATURES: dict[str, tuple[str, ...]] = {
    "WordPress": ("wp-content", "wp-includes", 'name="generator" content="wordpress'),
    "TYPO3": ("typo3temp", "typo3conf", 'name="generator" content="typo3'),
    "Joomla": ("/media/jui/", 'name="generator" content="joomla'),
    "Drupal": ("/sites/default/files", "drupal.settings", "drupal-"),
    "Contao": ("/files/contao", 'name="generator" content="contao'),
    "Shopify": ("cdn.shopify.com", "shopify-features"),
    "WooCommerce": ("woocommerce",),
    "Shopware": ("shopware", "/widgets/emotion"),
    "Wix": ("wix.com", "_wixcssinvoke", "wixstatic.com"),
    "Squarespace": ("squarespace.com", "static1.squarespace"),
    "Jimdo": ("jimdo.com", "jimstatic.com"),
    "Webflow": ("webflow.com", "w-webflow"),
    "IONOS MyWebsite": ("mywebsite-editor", "ionos.space"),
}

# Frontend-Frameworks / JS-Bibliotheken.
FRAMEWORK_SIGNATURES: dict[str, tuple[str, ...]] = {
    "React": ("data-reactroot", "react-dom", "_reactlisteningto"),
    "Next.js": ("__next_data__", "/_next/static"),
    "Vue.js": ("data-v-app", "vue.runtime", "__vue__"),
    "Nuxt": ("__nuxt", "/_nuxt/"),
    "Angular": ("ng-version", "ng-app"),
    "Svelte / SvelteKit": ("svelte-", "__sveltekit"),
    "jQuery": ("jquery",),
    "Bootstrap": ("bootstrap.min.css", "bootstrap.bundle"),
    "Tailwind CSS": ("tailwind",),
    "Elementor": ("elementor",),
}

# CDN / Hosting-Hinweise aus Response-Headern (Header-Name → Anbieter).
CDN_HEADER_HINTS: dict[str, str] = {
    "cf-ray": "Cloudflare",
    "cf-cache-status": "Cloudflare",
    "x-amz-cf-id": "Amazon CloudFront",
    "x-akamai-request-id": "Akamai",
    "x-fastly-request-id": "Fastly",
    "x-vercel-id": "Vercel",
    "x-nf-request-id": "Netlify",
    "x-github-request-id": "GitHub Pages",
    "x-served-by": "Fastly/Varnish",
}

_META_RE = re.compile(
    r"""<meta\s+[^>]*?(?:name|property)\s*=\s*["']([^"']+)["'][^>]*?content\s*=\s*["']([^"']*)["']""",
    re.I | re.S)
_META_REV_RE = re.compile(
    r"""<meta\s+[^>]*?content\s*=\s*["']([^"']*)["'][^>]*?(?:name|property)\s*=\s*["']([^"']+)["']""",
    re.I | re.S)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_LINK_REL_RE = re.compile(r"""<link\s+[^>]*rel\s*=\s*["']([^"']+)["'][^>]*>""", re.I)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
_LANG_RE = re.compile(r"<html[^>]*\slang\s*=\s*[\"']([^\"']+)[\"']", re.I)
_CHARSET_RE = re.compile(r"""<meta[^>]*charset\s*=\s*["']?([\w-]+)""", re.I)
_A_HREF_RE = re.compile(r"""<a\s+[^>]*href\s*=\s*["']([^"'#]+)["']""", re.I)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
_ALT_RE = re.compile(r"\balt\s*=", re.I)
_JSONLD_TYPE_RE = re.compile(r'"@type"\s*:\s*"([^"]+)"', re.I)
_GENERATOR_VER_RE = re.compile(r'content=["\']wordpress\s*([\d.]+)', re.I)


def _metas(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _META_RE.finditer(html):
        out.setdefault(m.group(1).strip().lower(), m.group(2).strip())
    for m in _META_REV_RE.finditer(html):     # content vor name/property
        out.setdefault(m.group(2).strip().lower(), m.group(1).strip())
    return out


def _headings(html: str) -> dict[str, int]:
    return {f"h{i}": len(re.findall(rf"<h{i}\b", html, re.I)) for i in range(1, 7)}


def _match_table(hay: str, table: dict[str, tuple[str, ...]]) -> list[str]:
    return sorted({name for name, sigs in table.items() if any(s in hay for s in sigs)})


def detect_trackers(hay: str) -> list[dict]:
    """Erkannte Drittdienste mit Risiko-Einstufung (sortiert: hohes Risiko zuerst)."""
    order = {"high": 0, "medium": 1, "low": 2}
    found = [{"name": name, "risk": risk}
             for name, (sigs, risk) in TRACKER_SIGNATURES.items()
             if any(s in hay for s in sigs)]
    found.sort(key=lambda t: (order.get(t["risk"], 3), t["name"]))
    return found


def link_stats(html: str, base_url: str) -> dict:
    """Interne/externe Verlinkung der Startseite (für SEO + Broken-Link-Stichprobe)."""
    host = (urlsplit(base_url).hostname or "").lower()
    internal: list[str] = []
    external = 0
    for href in _A_HREF_RE.findall(html):
        href = href.strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        absolute = urljoin(base_url, href)
        h = (urlsplit(absolute).hostname or "").lower()
        if not h or h == host:
            if absolute not in internal:
                internal.append(absolute)
        else:
            external += 1
    return {"internal": internal, "internal_count": len(internal), "external_count": external}


def extract_signals(final_url: str, html: str, headers: dict) -> dict:
    """Alle Fakten der Startseite als strukturierter Steckbrief (rein).

    `headers` = Response-Header mit **kleingeschriebenen** Keys.
    """
    hay = html.lower()
    metas = _metas(html)
    rels = {r.strip().lower() for raw in _LINK_REL_RE.findall(html) for r in raw.split()}

    title_m = _TITLE_RE.search(html)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""

    imgs = _IMG_RE.findall(html)
    img_no_alt = sum(1 for tag in imgs if not _ALT_RE.search(tag))

    trackers = detect_trackers(hay)
    cms = _match_table(hay, CMS_SIGNATURES)
    frameworks = _match_table(hay, FRAMEWORK_SIGNATURES)
    cmps = _match_table(hay, CMP_SIGNATURES)

    wp_ver = _GENERATOR_VER_RE.search(html)
    server = headers.get("server") or None
    powered = headers.get("x-powered-by") or None
    cdn = sorted({p for h, p in CDN_HEADER_HINTS.items() if h in headers})

    robots_meta = metas.get("robots", "")
    links = link_stats(html, final_url)

    # Google Fonts: extern eingebunden vs. lokal ausgeliefert.
    fonts_external = any(s in hay for s in ("fonts.googleapis.com", "fonts.gstatic.com"))

    return {
        "meta": {
            "title": title,
            "title_length": len(title),
            "description": metas.get("description", ""),
            "description_length": len(metas.get("description", "")),
            "canonical": "canonical" in rels,
            "robots": robots_meta,
            "noindex": "noindex" in robots_meta.lower(),
            "lang": (_LANG_RE.search(html).group(1) if _LANG_RE.search(html) else ""),
            "charset": (_CHARSET_RE.search(html).group(1) if _CHARSET_RE.search(html) else ""),
            "favicon": any(r in rels for r in ("icon", "shortcut", "apple-touch-icon")),
            "viewport": bool(metas.get("viewport")),
            "og": {k[3:]: v for k, v in metas.items() if k.startswith("og:")},
            "og_present": any(k.startswith("og:") for k in metas),
            "twitter_card": metas.get("twitter:card", ""),
            "twitter_present": any(k.startswith("twitter:") for k in metas),
        },
        "seo": {
            "headings": _headings(html),
            "images_total": len(imgs),
            "images_without_alt": img_no_alt,
            "structured_data": sorted(set(_JSONLD_TYPE_RE.findall(html)))[:10],
            "has_structured_data": "application/ld+json" in hay,
            "internal_links": links["internal_count"],
            "external_links": links["external_count"],
            "_internal_urls": links["internal"][:40],   # für die Broken-Link-Stichprobe
        },
        "tech": {
            "cms": cms,
            "frameworks": frameworks,
            "server": server,
            "powered_by": powered,
            "cdn": cdn,
            "wordpress_version": wp_ver.group(1) if wp_ver else None,
            "https": final_url.startswith("https://"),
        },
        "privacy": {
            "has_impressum": "impressum" in hay,
            "has_privacy": ("datenschutz" in hay or "privacy" in hay),
            "cmps": cmps,
            "has_cookie_banner": bool(cmps) or (
                "cookie" in hay and any(k in hay for k in
                                        ("einwillig", "zustimm", "consent", "akzeptier"))),
            "trackers": trackers,
            "high_risk_trackers": [t["name"] for t in trackers if t["risk"] == "high"],
            "google_fonts_external": fonts_external,
        },
    }
