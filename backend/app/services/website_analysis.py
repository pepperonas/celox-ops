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
from app.services.website_signals import extract_signals

ANALYSIS_VERSION = "2.0"

def _f(category_key: str, issue: str, severity: str) -> dict:
    return {"category_key": category_key, "category": CATEGORY_LABELS[category_key],
            "issue": issue, "severity": severity}


def analyze_html(final_scheme: str, html: str, headers_lower: dict,
                 load_time_ms: int, content_length: int,
                 final_url: str | None = None, extras: dict | None = None) -> dict:
    """Bewertet die extrahierten Signale (rein): Kategorie-Subscores + Befunde.

    Die Fakten kommen aus `website_signals.extract_signals` — hier wird nur
    geurteilt. `extras` liefert optionale Netzwerk-Zusatzsignale (robots.txt,
    sitemap.xml, Broken-Link-Stichprobe, Redirect-Kette).
    """
    url = final_url or f"{final_scheme}://"
    sig = extract_signals(url, html, headers_lower)
    extras = extras or {}
    meta_s, seo_s, tech_s, priv_s = sig["meta"], sig["seo"], sig["tech"], sig["privacy"]

    findings: list[dict] = []
    sub = {"datenschutz": 100, "performance": 100, "seo": 100, "technik": 100, "ux": 100}

    def deduct(cat, pts, issue, sev):
        sub[cat] = max(0, sub[cat] - pts)
        findings.append(_f(cat, issue, sev))

    # ---- Datenschutz ----
    if not priv_s["has_impressum"]:
        deduct("datenschutz", 40, "Kein Impressum verlinkt (§ 5 DDG-Pflicht)", "critical")
    if not priv_s["has_privacy"]:
        deduct("datenschutz", 40, "Keine Datenschutzerklärung verlinkt (Art. 13 DSGVO)", "critical")
    high = priv_s["high_risk_trackers"]
    if high and not priv_s["has_cookie_banner"]:
        deduct("datenschutz", 30,
               f"Einwilligungspflichtige Dienste ohne Cookie-Banner: {', '.join(high)}", "critical")
    elif high:
        deduct("datenschutz", 5,
               f"Einwilligungspflichtige Dienste (Banner erkannt): {', '.join(high)}", "info")
    if priv_s["google_fonts_external"]:
        deduct("datenschutz", 10,
               "Google Fonts extern eingebunden — IP-Übermittlung in die USA, Abmahnrisiko", "warning")
    embeds = [t["name"] for t in priv_s["trackers"] if t["risk"] == "medium"]
    if embeds and not priv_s["has_cookie_banner"]:
        deduct("datenschutz", 8,
               f"Eingebettete Drittinhalte ohne Einwilligung: {', '.join(embeds)}", "warning")

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
    if not meta_s["title"]:
        deduct("seo", 25, "Kein <title> — Suchmaschinen zeigen keinen Titel", "critical")
    elif meta_s["title_length"] < 10:
        deduct("seo", 8, f"Titel sehr kurz ({meta_s['title_length']} Zeichen)", "warning")
    elif meta_s["title_length"] > 65:
        deduct("seo", 3, f"Titel zu lang ({meta_s['title_length']} Zeichen) — wird abgeschnitten", "info")
    if not meta_s["description"]:
        deduct("seo", 15, "Keine Meta-Description", "warning")
    elif not 50 <= meta_s["description_length"] <= 165:
        deduct("seo", 3,
               f"Meta-Description ungünstig lang ({meta_s['description_length']} Zeichen)", "info")
    h = seo_s["headings"]
    if h["h1"] == 0:
        deduct("seo", 10, "Keine H1-Überschrift — Seitenstruktur fehlt", "warning")
    elif h["h1"] > 1:
        deduct("seo", 5, f"{h['h1']} H1-Überschriften — genau eine ist optimal", "info")
    if h["h1"] and not h["h2"]:
        deduct("seo", 3, "Keine H2-Ebene — flache Überschriftenstruktur", "info")
    if not meta_s["canonical"]:
        deduct("seo", 5, "Kein Canonical-Tag", "info")
    if not seo_s["has_structured_data"]:
        deduct("seo", 8, "Keine strukturierten Daten (Schema.org/JSON-LD)", "info")
    if not meta_s["og_present"]:
        deduct("seo", 5, "Kein OpenGraph — Links in sozialen Netzen ohne Vorschaubild", "info")
    elif not meta_s["twitter_present"]:
        deduct("seo", 2, "Keine Twitter-Card-Meta-Daten", "info")
    if meta_s["noindex"]:
        deduct("seo", 40, "Seite auf noindex — wird von Suchmaschinen nicht indexiert", "critical")
    if extras.get("robots_txt") is False:
        deduct("seo", 5, "Keine robots.txt gefunden", "info")
    if extras.get("sitemap") is False:
        deduct("seo", 8, "Keine sitemap.xml gefunden", "warning")
    broken = extras.get("broken_links") or []
    if broken:
        deduct("seo", min(15, 3 * len(broken)),
               f"{len(broken)} defekte interne Links (Stichprobe): {', '.join(broken[:3])}", "warning")

    # ---- Technik & Sicherheit ----
    if final_scheme != "https":
        deduct("technik", 40, "Kein HTTPS — Verbindung unverschlüsselt", "critical")
    if not meta_s["viewport"]:
        deduct("technik", 20, "Kein Viewport-Meta-Tag — nicht mobiloptimiert", "critical")
    if "content-security-policy" not in headers_lower:
        deduct("technik", 5, "Kein Content-Security-Policy-Header", "info")
    if "x-frame-options" not in headers_lower:
        deduct("technik", 5, "Kein X-Frame-Options-Header (Clickjacking)", "info")
    if "strict-transport-security" not in headers_lower:
        deduct("technik", 5, "Kein HSTS-Header", "info")
    if not meta_s["charset"]:
        deduct("technik", 3, "Keine Zeichensatz-Deklaration (charset)", "info")
    if tech_s["wordpress_version"]:
        deduct("technik", 5,
               f"WordPress-Version {tech_s['wordpress_version']} öffentlich sichtbar", "warning")
    if tech_s["powered_by"]:
        deduct("technik", 3,
               f"X-Powered-By verrät die Server-Software ({tech_s['powered_by'][:40]})", "info")
    if tech_s["server"] and any(c.isdigit() for c in tech_s["server"]):
        deduct("technik", 3,
               f"Server-Header verrät die Version ({tech_s['server'][:40]})", "info")
    if "jQuery" in tech_s["frameworks"] and any(
            x in html.lower() for x in ("jquery-1.", "jquery-2.")):
        deduct("technik", 3, "Veraltete jQuery-Version (1.x/2.x) eingebunden", "info")

    # ---- UX / Barrierefreiheit ----
    if seo_s["images_total"] and seo_s["images_without_alt"]:
        pct = int(seo_s["images_without_alt"] / seo_s["images_total"] * 100)
        deduct("ux", min(25, seo_s["images_without_alt"] * 2),
               f"{seo_s['images_without_alt']}/{seo_s['images_total']} Bilder ohne Alt-Text ({pct}%)",
               "warning")
    if not meta_s["viewport"]:
        deduct("ux", 15, "Nicht responsive (kein Viewport)", "warning")
    if not meta_s["favicon"]:
        deduct("ux", 5, "Kein Favicon", "info")
    if not meta_s["lang"]:
        deduct("ux", 5, "Keine Sprachauszeichnung (html lang)", "info")

    technologies = sorted(set(
        tech_s["cms"] + tech_s["frameworks"] + tech_s["cdn"]
        + [t["name"] for t in priv_s["trackers"]]
    ))
    meta_out = {
        "load_time_ms": load_time_ms, "content_length": content_length,
        "trackers": [t["name"] for t in priv_s["trackers"]],
        "has_cookie_banner": priv_s["has_cookie_banner"],
        "has_impressum": priv_s["has_impressum"], "has_privacy": priv_s["has_privacy"],
        "signals": {**sig, "seo": {k: v for k, v in seo_s.items() if not k.startswith("_")},
                    "extras": {k: v for k, v in extras.items() if k != "internal_urls"}},
    }
    return {"subscores": sub, "findings": findings,
            "technologies": technologies, "meta": meta_out, "signals": sig}


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


async def _safe_get(url: str, verify: bool, chain: list | None = None):
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
            if chain is not None:
                chain.append({"url": current, "status": resp.status_code})
            loc = resp.headers.get("location")
            if resp.is_redirect and loc:
                current = str(resp.url.join(loc))
                continue
            return resp
        raise _Blocked("zu viele Redirects")


async def fetch_extras(base_url: str, internal_urls: list[str]) -> dict:
    """Zusatzsignale, die weitere Requests brauchen (defensiv: Fehler → weglassen).

    - robots.txt vorhanden? → daraus ggf. die Sitemap-Angabe
    - sitemap.xml vorhanden?
    - Broken-Link-Stichprobe: max. 15 interne Links per HEAD (parallel)

    Nur same-host (der Host wurde beim Hauptabruf bereits gegen interne Ziele
    geprüft) — keine neue SSRF-Fläche.
    """
    p = urlsplit(base_url)
    origin = f"{p.scheme}://{p.netloc}"
    host = (p.hostname or "").lower()
    out: dict = {}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers=_UA) as client:
            robots = None
            try:
                r = await client.get(f"{origin}/robots.txt")
                robots = r.text if r.status_code == 200 and "text" in r.headers.get(
                    "content-type", "text/plain") else None
                out["robots_txt"] = robots is not None
            except httpx.HTTPError:
                out["robots_txt"] = None

            sitemap_url = f"{origin}/sitemap.xml"
            if robots:
                m = re.search(r"(?im)^\s*sitemap:\s*(\S+)", robots)
                if m:
                    sitemap_url = m.group(1).strip()
            try:
                sm = await client.head(sitemap_url)
                if sm.status_code >= 400:
                    sm = await client.get(sitemap_url)
                out["sitemap"] = sm.status_code < 400
                if out["sitemap"]:
                    out["sitemap_url"] = sitemap_url
            except httpx.HTTPError:
                out["sitemap"] = None

            # Broken-Link-Stichprobe (nur same-host, max. 15, parallel)
            sample = [u for u in internal_urls
                      if (urlsplit(u).hostname or "").lower() == host][:15]
            if sample:
                async def check(u: str):
                    try:
                        r = await client.head(u)
                        if r.status_code >= 400:      # manche Server mögen kein HEAD
                            r = await client.get(u)
                        return None if r.status_code < 400 else f"{r.status_code} {u}"
                    except httpx.HTTPError:
                        return f"Fehler {u}"
                results = await asyncio.gather(*[check(u) for u in sample],
                                               return_exceptions=True)
                broken = [r for r in results if isinstance(r, str)]
                out["links_checked"] = len(sample)
                out["broken_links"] = broken
    except Exception:  # nie die Hauptanalyse killen
        return out
    return out


def _cert_failed(url: str) -> dict:
    """Ungültiges TLS-Zertifikat → kritischer Befund OHNE den (unverifizierten)
    Seiteninhalt zu laden (MITM-Schutz)."""
    findings = [_f("technik", "TLS-Zertifikat ungültig/abgelaufen oder nicht vertrauenswürdig", "critical")]
    result = summarize({"datenschutz": None, "performance": None, "seo": None,
                        "technik": 0, "ux": None, "ki": None}, findings)
    result.update({"url": url, "analysis_version": ANALYSIS_VERSION, "technologies": [],
                   "meta": {"reachable": False, "reason": "TLS-Zertifikat ungültig"}})
    return result


async def _load(url: str) -> tuple[object | None, int, dict | None, str | None, list]:
    """Lädt die Seite SSRF-sicher mit strikter TLS-Prüfung.
    Rückgabe: (resp, load_time_ms, error_result, clean_url) — bei Fehler ist
    `error_result` ein fertiges Analyse-Summary und `resp` None."""
    clean = _sanitize_url(url)
    chain: list = []
    if clean is None:
        return None, 0, _unreachable((url or "").strip(), "Ungültige URL"), None, chain
    try:
        start = time.time()
        resp = await _safe_get(clean, verify=True, chain=chain)
        return resp, int((time.time() - start) * 1000), None, clean, chain
    except _Blocked as e:
        return None, 0, _unreachable(clean, f"Analyse abgelehnt: {e}"), clean, chain
    except httpx.ConnectError as e:
        if "certificate" in str(e).lower() or "ssl" in str(e).lower():
            return None, 0, _cert_failed(clean), clean, chain
        return None, 0, _unreachable(clean, "Website nicht erreichbar — Verbindung fehlgeschlagen"), clean, chain
    except httpx.TimeoutException:
        return None, 0, _unreachable(clean, "Website-Timeout nach 15 Sekunden"), clean, chain
    except httpx.HTTPError:
        return None, 0, _unreachable(clean, "Website nicht erreichbar — Verbindung fehlgeschlagen"), clean, chain


def _technical(resp, load_time_ms: int, extras: dict | None = None) -> dict:
    headers_lower = {k.lower(): v.lower() for k, v in resp.headers.items()}
    return analyze_html(resp.url.scheme, resp.text, headers_lower,
                        load_time_ms, len(resp.content),
                        final_url=str(resp.url), extras=extras)


def _finalize(resp, analyzed: dict, extra_meta: dict | None = None,
              ai_review: dict | None = None, pagespeed: dict | None = None) -> dict:
    result = summarize(analyzed["subscores"], analyzed["findings"])
    result.update({
        "url": str(resp.url),
        "analysis_version": ANALYSIS_VERSION,
        "technologies": analyzed["technologies"],
        "meta": {"reachable": True, **analyzed["meta"], **(extra_meta or {})},
    })
    if ai_review is not None:
        result["ai_review"] = ai_review
    if pagespeed is not None:
        result["pagespeed"] = pagespeed
    return result


async def fetch_and_analyze(url: str) -> dict:
    """Holt die Seite und liefert das vollständige Analyse-Summary
    (Gesamtscore/Ampel/Kategorien/Empfehlungen + Technologien + meta).

    SSRF-Schutz: Schema http/https erzwungen, userinfo entfernt, jeder Redirect-
    Hop gegen interne/private/Metadaten-IPs geprüft (Auto-Redirects aus).
    TLS wird strikt verifiziert; ein ungültiges Zertifikat wird zu einem kritischen
    Technik-Befund — der Inhalt wird NICHT ungeprüft geladen (kein MITM-Vektor)."""
    resp, load_time_ms, err, _, chain = await _load(url)
    if err is not None:
        return err
    first = _technical(resp, load_time_ms)
    extras = await fetch_extras(str(resp.url), first["signals"]["seo"]["_internal_urls"])
    extras["redirects"] = chain
    return _finalize(resp, _technical(resp, load_time_ms, extras))


async def analyze_deep(url: str, *, ai=None, model: str | None = None, usage=None,
                       with_pagespeed: bool = False, pagespeed_strategy: str = "mobile") -> dict:
    """Tiefenanalyse (A2, opt-in): technische Basis + optional PageSpeed
    (überschreibt den heuristischen Performance-Subscore) + optional KI-
    Qualitätsbewertung (liefert den `ki`-Subscore).

    Beide Zusatzquellen sind defensiv: fällt eine aus, bleibt die technische
    Analyse vollständig gültig (kein Abbruch)."""
    resp, load_time_ms, err, clean, chain = await _load(url)
    if err is not None:
        return err
    first = _technical(resp, load_time_ms)
    extras = await fetch_extras(str(resp.url), first["signals"]["seo"]["_internal_urls"])
    extras["redirects"] = chain
    analyzed = _technical(resp, load_time_ms, extras)
    final_url = str(resp.url)
    extra_meta: dict = {}

    pagespeed = None
    if with_pagespeed:
        from app.services.website_pagespeed import fetch_pagespeed
        pagespeed = await fetch_pagespeed(final_url, pagespeed_strategy)
        if pagespeed and pagespeed["scores"].get("performance") is not None:
            # Gemessener Lighthouse-Wert schlägt die Ladezeit-Heuristik.
            analyzed["subscores"]["performance"] = pagespeed["scores"]["performance"]
            extra_meta["performance_source"] = "pagespeed"
        elif with_pagespeed:
            extra_meta["pagespeed_error"] = "PageSpeed nicht verfügbar"

    ai_review = None
    if ai is not None and model:
        from app.services.website_ai_review import extract_text, review_website
        try:
            text = extract_text(resp.text)
            ai_review = await review_website(ai, model, final_url, text,
                                             analyzed["meta"], analyzed["technologies"], usage)
            analyzed["subscores"]["ki"] = ai_review["score"]
        except Exception as e:  # KI-Ausfall darf die Analyse nicht killen
            extra_meta["ai_error"] = str(e)[:200]

    return _finalize(resp, analyzed, extra_meta, ai_review, pagespeed)
