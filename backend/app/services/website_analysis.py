"""Website-Analyse: technische Prüfungen → Kategorie-Subscores + Befunde.

`analyze_html` ist rein (nimmt bereits geladenes HTML/Header/Timing) und damit
testbar; `fetch_and_analyze` holt die Seite (httpx) und ruft es auf. Das Ergebnis
wird vom `website_scoring`-Service zum Gesamtscore verrechnet.

Kategorien (A1, technisch): datenschutz, performance, seo, technik, ux.
Die KI-Qualitätsbewertung (`ki`) kommt in A2 (opt-in) dazu.
"""
import asyncio
import ipaddress
import re
import socket
import time
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.services.website_scoring import CATEGORY_LABELS, summarize

ANALYSIS_VERSION = "1.0"

# Bekannte Consent-Management-Plattformen (Cookie-Banner-Erkennung).
_CMP = ("cookiebot", "usercentrics", "borlabs", "cookieconsent", "cookie-consent",
        "klaro", "complianz", "consentmanager", "onetrust", "cookiefirst")
# Externe Dienste mit Datenschutz-Relevanz (Tracker/Third-Party).
_TRACKERS = {
    "Google Analytics": ("google-analytics.com", "googletagmanager.com", "gtag("),
    "Google Fonts": ("fonts.googleapis.com", "fonts.gstatic.com"),
    "Facebook Pixel": ("connect.facebook.net", "fbevents.js"),
    "YouTube-Einbettung": ("youtube.com/embed", "youtu.be"),
    "Google Maps": ("maps.googleapis.com", "google.com/maps/embed"),
    "Hotjar": ("hotjar.com",),
    "Matomo/Piwik": ("matomo.js", "piwik.js"),
    "Google Ads/DoubleClick": ("doubleclick.net", "googleadservices.com"),
}


def _f(category_key: str, issue: str, severity: str) -> dict:
    return {"category_key": category_key, "category": CATEGORY_LABELS[category_key],
            "issue": issue, "severity": severity}


def analyze_html(final_scheme: str, html_lower: str, headers_lower: dict,
                 load_time_ms: int, content_length: int) -> dict:
    """Reine technische Analyse. Rückgabe: {subscores, findings, technologies, meta}."""
    findings: list[dict] = []
    technologies: list[str] = []
    sub = {"datenschutz": 100, "performance": 100, "seo": 100, "technik": 100, "ux": 100}

    def deduct(cat, pts, issue, sev):
        sub[cat] = max(0, sub[cat] - pts)
        findings.append(_f(cat, issue, sev))

    # ---- Datenschutz ----
    has_impressum = "impressum" in html_lower
    has_privacy = "datenschutz" in html_lower or "privacy" in html_lower
    has_banner = any(c in html_lower for c in _CMP) or (
        "cookie" in html_lower and any(k in html_lower for k in ("einwillig", "zustimm", "consent", "akzeptier"))
    )
    found_trackers = [name for name, needles in _TRACKERS.items()
                      if any(n in html_lower for n in needles)]
    technologies.extend(found_trackers)
    if not has_impressum:
        deduct("datenschutz", 40, "Kein Impressum verlinkt (§ 5 DDG-Pflicht)", "critical")
    if not has_privacy:
        deduct("datenschutz", 40, "Keine Datenschutzerklärung verlinkt (Art. 13 DSGVO)", "critical")
    if found_trackers and not has_banner:
        deduct("datenschutz", 25,
               f"Externe Dienste ohne Cookie-Banner/Einwilligung: {', '.join(found_trackers)}", "warning")
    if "Google Fonts" in found_trackers:
        deduct("datenschutz", 10,
               "Google Fonts extern eingebunden — IP-Übermittlung, Abmahnrisiko", "warning")

    # ---- Performance ----
    if load_time_ms > 5000:
        deduct("performance", 40, f"Sehr langsam: {load_time_ms/1000:.1f}s Ladezeit", "critical")
    elif load_time_ms > 3000:
        deduct("performance", 20, f"Langsam: {load_time_ms/1000:.1f}s Ladezeit", "warning")
    elif load_time_ms > 1500:
        deduct("performance", 8, f"Ladezeit {load_time_ms/1000:.1f}s — Luft nach oben", "info")
    if content_length > 3_000_000:
        deduct("performance", 15, f"Sehr große Seite: {content_length/1_000_000:.1f} MB", "warning")
    elif content_length > 800_000:
        deduct("performance", 5, f"Große Seite: {content_length/1000:.0f} KB", "info")

    # ---- SEO ----
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html_lower, re.DOTALL)
    title = (title_m.group(1).strip() if title_m else "")
    if not title:
        deduct("seo", 25, "Kein <title> — Suchmaschinen zeigen keinen Titel", "critical")
    elif len(title) < 10:
        deduct("seo", 8, f"Titel sehr kurz ({len(title)} Zeichen)", "warning")
    if 'name="description"' not in html_lower and "name='description'" not in html_lower:
        deduct("seo", 15, "Keine Meta-Description", "warning")
    if "<h1" not in html_lower:
        deduct("seo", 10, "Keine H1-Überschrift — Seitenstruktur fehlt", "warning")
    if 'rel="canonical"' not in html_lower and "rel='canonical'" not in html_lower:
        deduct("seo", 5, "Kein Canonical-Tag", "info")
    if "application/ld+json" not in html_lower:
        deduct("seo", 8, "Keine strukturierten Daten (Schema.org/JSON-LD)", "info")

    # ---- Technik & Sicherheit ----
    if final_scheme != "https":
        deduct("technik", 40, "Kein HTTPS — Verbindung unverschlüsselt", "critical")
    has_viewport = 'name="viewport"' in html_lower or "name='viewport'" in html_lower
    if not has_viewport:
        deduct("technik", 20, "Kein Viewport-Meta-Tag — nicht mobiloptimiert", "critical")
    if "content-security-policy" not in headers_lower:
        deduct("technik", 5, "Kein Content-Security-Policy-Header", "info")
    if "x-frame-options" not in headers_lower:
        deduct("technik", 5, "Kein X-Frame-Options-Header (Clickjacking)", "info")
    if "strict-transport-security" not in headers_lower:
        deduct("technik", 5, "Kein HSTS-Header", "info")
    if "charset" not in html_lower[:2000]:
        deduct("technik", 3, "Keine Zeichensatz-Deklaration (charset)", "info")

    # ---- Technologie-Erkennung (informativ) ----
    if "wp-content" in html_lower or 'name="generator" content="wordpress' in html_lower:
        technologies.append("WordPress")
        gen = re.search(r'name="generator"[^>]*content="wordpress\s*([\d.]+)', html_lower)
        if gen:
            deduct("technik", 5, f"WordPress-Version {gen.group(1)} öffentlich sichtbar", "warning")
    if "jquery" in html_lower and any(x in html_lower for x in ("jquery-1.", "jquery-2.")):
        technologies.append("jQuery (alt)")
    if "wix.com" in html_lower or "_wixcssinvoke" in html_lower:
        technologies.append("Wix")
    if "shopify" in html_lower:
        technologies.append("Shopify")

    # ---- UX / Barrierefreiheit ----
    img_count = html_lower.count("<img")
    img_no_alt = len(re.findall(r"<img(?![^>]*alt=)[^>]*>", html_lower))
    if img_count and img_no_alt:
        pct = int(img_no_alt / img_count * 100)
        deduct("ux", min(25, img_no_alt * 2), f"{img_no_alt}/{img_count} Bilder ohne Alt-Text ({pct}%)", "warning")
    if not has_viewport:
        deduct("ux", 15, "Nicht responsive (kein Viewport)", "warning")
    if 'rel="icon"' not in html_lower and "rel='icon'" not in html_lower and "shortcut icon" not in html_lower:
        deduct("ux", 5, "Kein Favicon", "info")
    if "<html lang=" not in html_lower and "<html  lang=" not in html_lower:
        deduct("ux", 5, "Keine Sprachauszeichnung (html lang)", "info")

    meta = {"load_time_ms": load_time_ms, "content_length": content_length,
            "trackers": found_trackers, "has_cookie_banner": has_banner,
            "has_impressum": has_impressum, "has_privacy": has_privacy}
    return {"subscores": sub, "findings": findings,
            "technologies": sorted(set(technologies)), "meta": meta}


def _unreachable(url: str, reason: str) -> dict:
    findings = [_f("technik", reason, "critical")]
    result = summarize({"datenschutz": None, "performance": 0, "seo": None,
                        "technik": 0, "ux": None, "ki": None}, findings)
    result.update({"url": url, "analysis_version": ANALYSIS_VERSION,
                   "technologies": [], "meta": {"reachable": False, "reason": reason}})
    return result


_UA = {"User-Agent": "Mozilla/5.0 (compatible; celox-ops-analyzer/2.0)"}
_MAX_REDIRECTS = 5


class _Blocked(Exception):
    """Ziel-URL aus Sicherheitsgründen abgelehnt (SSRF-Schutz)."""


def _host_is_public(hostname: str) -> bool:
    """True nur, wenn ALLE aufgelösten Adressen öffentlich sind (SSRF-Schutz).
    Blockt loopback/privat/link-local (169.254 = Cloud-Metadaten)/reserved/
    multicast/unspecified — für jede aufgelöste Adresse, nicht nur die erste.
    Blockierend (DNS) → vom Aufrufer via asyncio.to_thread ausgeführt."""
    hostname = (hostname or "").rstrip(".").lower()
    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True


def _sanitize_url(raw: str) -> str | None:
    """Erzwingt http/https, entfernt userinfo (user:pass@), normalisiert den Host.
    Rückgabe: bereinigte URL oder None (ungültig)."""
    raw = (raw or "").strip()
    if not raw:
        return None
    low = raw.lower()
    if not low.startswith(("http://", "https://")):
        if re.match(r"^[a-z][a-z0-9+.\-]*://", low):
            return None  # fremdes Schema (ftp://, file://, …) → ablehnen
        raw = "https://" + raw  # nacktes Domain → https voranstellen
    p = urlsplit(raw)
    if p.scheme not in ("http", "https") or not p.hostname:
        return None
    try:
        port = p.port
    except ValueError:
        return None
    netloc = p.hostname.rstrip(".").lower()
    if port:
        netloc += f":{port}"
    return urlunsplit((p.scheme, netloc, p.path or "/", p.query, ""))


async def _safe_get(url: str, verify: bool):
    """GET OHNE Auto-Redirects; jeder (Redirect-)Hop wird gegen interne/private
    Ziele geprüft (SSRF). Wirft `_Blocked` bei nicht-öffentlichem Ziel."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, verify=verify) as client:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            p = urlsplit(current)
            if p.scheme not in ("http", "https") or not p.hostname:
                raise _Blocked("ungültige URL")
            if not await asyncio.to_thread(_host_is_public, p.hostname):
                raise _Blocked("internes/privates Ziel")
            resp = await client.get(current, headers=_UA)
            loc = resp.headers.get("location")
            if resp.is_redirect and loc:
                current = str(resp.url.join(loc))
                continue
            return resp
        raise _Blocked("zu viele Redirects")


def _cert_failed(url: str) -> dict:
    """Ungültiges TLS-Zertifikat → kritischer Befund OHNE den (unverifizierten)
    Seiteninhalt zu laden (MITM-Schutz)."""
    findings = [_f("technik", "TLS-Zertifikat ungültig/abgelaufen oder nicht vertrauenswürdig", "critical")]
    result = summarize({"datenschutz": None, "performance": None, "seo": None,
                        "technik": 0, "ux": None, "ki": None}, findings)
    result.update({"url": url, "analysis_version": ANALYSIS_VERSION, "technologies": [],
                   "meta": {"reachable": False, "reason": "TLS-Zertifikat ungültig"}})
    return result


async def fetch_and_analyze(url: str) -> dict:
    """Holt die Seite und liefert das vollständige Analyse-Summary
    (Gesamtscore/Ampel/Kategorien/Empfehlungen + Technologien + meta).

    SSRF-Schutz: Schema http/https erzwungen, userinfo entfernt, jeder Redirect-
    Hop gegen interne/private/Metadaten-IPs geprüft (Auto-Redirects aus).
    TLS wird strikt verifiziert; ein ungültiges Zertifikat wird zu einem kritischen
    Technik-Befund — der Inhalt wird NICHT ungeprüft geladen (kein MITM-Vektor)."""
    clean = _sanitize_url(url)
    if clean is None:
        return _unreachable((url or "").strip(), "Ungültige URL")
    try:
        start = time.time()
        resp = await _safe_get(clean, verify=True)
        load_time_ms = int((time.time() - start) * 1000)
    except _Blocked as e:
        return _unreachable(clean, f"Analyse abgelehnt: {e}")
    except httpx.ConnectError as e:
        if "certificate" in str(e).lower() or "ssl" in str(e).lower():
            return _cert_failed(clean)
        return _unreachable(clean, "Website nicht erreichbar — Verbindung fehlgeschlagen")
    except httpx.TimeoutException:
        return _unreachable(clean, "Website-Timeout nach 15 Sekunden")
    except httpx.HTTPError:
        return _unreachable(clean, "Website nicht erreichbar — Verbindung fehlgeschlagen")

    html_lower = resp.text.lower()
    headers_lower = {k.lower(): v.lower() for k, v in resp.headers.items()}
    analyzed = analyze_html(resp.url.scheme, html_lower, headers_lower,
                            load_time_ms, len(resp.content))
    result = summarize(analyzed["subscores"], analyzed["findings"])
    result.update({
        "url": str(resp.url),
        "analysis_version": ANALYSIS_VERSION,
        "technologies": analyzed["technologies"],
        "meta": {"reachable": True, **analyzed["meta"]},
    })
    return result
