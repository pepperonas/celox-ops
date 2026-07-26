"""Leichte Anreicherung von Discovery-Kandidaten (vor dem Import).

Ziel: aus EINEM Abruf der Startseite die Felder gewinnen, die einen Kandidaten
qualifizierbar machen — Kurzbeschreibung, Social-Profile, Tech-Stack,
Datenschutz-Ampel und (falls die Quelle keine liefert) eine Kontakt-E-Mail.
Bewusst **billig**: keine PageSpeed-, keine KI-Kosten, ~1–3 s pro Kandidat,
parallelisiert.

Ein Zusatzabruf ist erlaubt: findet die Startseite keine E-Mail, wird **eine**
verlinkte Impressum-/Kontaktseite nachgeladen (dort steht sie in Deutschland
praktisch immer). Mehr Requests machen wir nicht — die Tiefe liefert später die
vollständige Website-Analyse.

Alle Extraktoren sind rein (HTML rein, Fakten raus) und damit netzfrei testbar;
der Abruf läuft über den SSRF-geprüften `_safe_get` der Website-Analyse.
"""
import asyncio
import re
from urllib.parse import urljoin, urlsplit

from app.services.website_analysis import _safe_get, _sanitize_url
from app.services.website_signals import extract_signals

# --------------------------------------------------------------------------- #
#  Social-Profile
# --------------------------------------------------------------------------- #
# Reihenfolge = Anzeigereihenfolge. Muster bewusst eng (Profil-/Seiten-URLs),
# damit Share-Buttons (…/sharer.php?u=) nicht als eigenes Profil zählen.
SOCIAL_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("linkedin", "LinkedIn", re.compile(r"linkedin\.com/(?:company|in|showcase)/[\w\-.%]+", re.I)),
    ("xing", "Xing", re.compile(r"xing\.com/(?:companies|profile|pages)/[\w\-.%]+", re.I)),
    ("facebook", "Facebook", re.compile(r"facebook\.com/(?!sharer|share\.php)[\w\-.%]+", re.I)),
    ("instagram", "Instagram", re.compile(r"instagram\.com/[\w\-.%]+", re.I)),
    ("youtube", "YouTube", re.compile(r"youtube\.com/(?:@|c/|channel/|user/)[\w\-.%]+", re.I)),
    ("twitter", "X / Twitter", re.compile(r"(?:twitter|x)\.com/(?!intent|share)[\w\-.%]+", re.I)),
    ("tiktok", "TikTok", re.compile(r"tiktok\.com/@[\w\-.%]+", re.I)),
    ("github", "GitHub", re.compile(r"github\.com/[\w\-.%]+", re.I)),
]
SOCIAL_LABELS = {key: label for key, label, _ in SOCIAL_PATTERNS}

_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)


def extract_socials(html: str) -> dict[str, str]:
    """Erstes Profil je Netzwerk (aus den href-Attributen). Rein."""
    hrefs = _HREF_RE.findall(html or "")
    out: dict[str, str] = {}
    for href in hrefs:
        for key, _label, pat in SOCIAL_PATTERNS:
            if key in out:
                continue
            m = pat.search(href)
            if m:
                out[key] = "https://" + m.group(0).lstrip("/")
    return out


# --------------------------------------------------------------------------- #
#  Kontakt-E-Mail
# --------------------------------------------------------------------------- #
_MAILTO_RE = re.compile(r"""mailto:([^"'?>\s]+)""", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
# Technische/fremde Adressen, die nie ein Kontakt sind.
_EMAIL_BLOCK = re.compile(
    r"(no-?reply|do-?not-?reply|example\.|sentry\.io|wixpress|@sentry|"
    r"postmaster@|abuse@|@localhost|\.png$|\.jpg$|\.webp$|u003e)", re.I)
# Präferenz für die Kaltakquise: allgemeine Firmenpostfächer zuerst.
_EMAIL_PREF = ("kontakt", "info", "mail", "office", "buero", "büro", "anfrage", "service")


def extract_emails(html: str) -> list[str]:
    """Alle plausiblen E-Mail-Adressen (mailto: zuerst), dedupliziert. Rein."""
    found: list[str] = []
    for raw in _MAILTO_RE.findall(html or "") + _EMAIL_RE.findall(html or ""):
        addr = raw.strip().strip(".,;:").lower()
        # HTML-Entity-Reste (&#64; etc. sind hier schon Text) grob abfangen
        if "@" not in addr or addr.count("@") != 1 or _EMAIL_BLOCK.search(addr):
            continue
        if len(addr) > 200 or addr in found:
            continue
        found.append(addr)
    return found


def pick_email(emails: list[str]) -> str | None:
    """Beste Kontaktadresse: allgemeines Firmenpostfach vor Personenadresse. Rein."""
    if not emails:
        return None
    for pref in _EMAIL_PREF:
        for addr in emails:
            if addr.split("@", 1)[0].startswith(pref):
                return addr
    return emails[0]


# --------------------------------------------------------------------------- #
#  Datenschutz-Ampel (grobe Vorstufe der vollen Analyse)
# --------------------------------------------------------------------------- #
def privacy_rating(privacy: dict) -> str:
    """gruen | gelb | rot aus den Datenschutz-Signalen. Rein.

    rot  = Pflichtangabe fehlt ODER einwilligungspflichtiger Tracker ohne Banner
    gelb = Google Fonts extern ODER Tracker vorhanden (mit Banner)
    """
    p = privacy or {}
    high = list(p.get("high_risk_trackers") or [])
    banner = bool(p.get("has_cookie_banner"))
    if not p.get("has_impressum") or not p.get("has_privacy"):
        return "rot"
    if high and not banner:
        return "rot"
    if p.get("google_fonts_external") or p.get("trackers"):
        return "gelb"
    return "gruen"


def privacy_hint(privacy: dict) -> str | None:
    """Ein kurzer, belegter Satz zum Ampel-Grund (keine Wertung erfinden). Rein."""
    p = privacy or {}
    if not p.get("has_impressum"):
        return "kein Impressum gefunden"
    if not p.get("has_privacy"):
        return "keine Datenschutzerklärung gefunden"
    high = list(p.get("high_risk_trackers") or [])
    if high and not p.get("has_cookie_banner"):
        return f"{high[0]} ohne Cookie-Banner"
    if p.get("google_fonts_external"):
        return "Google Fonts extern geladen"
    if p.get("trackers"):
        return f"{len(p['trackers'])} Dienst(e) eingebunden"
    return None


# --------------------------------------------------------------------------- #
#  Zusammenbau
# --------------------------------------------------------------------------- #
_CONTACT_LINK_RE = re.compile(
    r"""href\s*=\s*["']([^"']*(?:impressum|imprint|kontakt|contact)[^"']*)["']""", re.I)


def contact_page_url(html: str, base_url: str) -> str | None:
    """Erste verlinkte Impressum-/Kontaktseite (same-host, absolut). Rein."""
    host = (urlsplit(base_url).hostname or "").lower()
    for href in _CONTACT_LINK_RE.findall(html or ""):
        if href.lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if (urlsplit(absolute).hostname or "").lower() == host:
            return absolute
    return None


def enrichment_from_html(final_url: str, html: str, headers: dict) -> dict:
    """Startseiten-HTML → Anreicherungsfelder. Rein (nutzt die Phase-1-Signale)."""
    sig = extract_signals(final_url, html, headers or {})
    meta = sig["meta"]
    tech = sig["tech"]
    desc = (meta.get("description") or "").strip()
    if not desc:
        # Fallback: der Titel sagt oft schon, was die Firma tut.
        desc = (meta.get("title") or "").strip()
    techs = list(tech.get("cms") or []) + list(tech.get("frameworks") or [])
    return {
        "description": desc[:300] or None,
        "socials": extract_socials(html),
        "technologies": techs[:6],
        "privacy_rating": privacy_rating(sig["privacy"]),
        "privacy_hint": privacy_hint(sig["privacy"]),
        "emails": extract_emails(html),
        "enriched": True,
    }


def merge_enrichment(row: dict, enriched: dict) -> dict:
    """Anreicherung auf einen Kandidaten legen — **nie** vorhandene Quelldaten
    überschreiben (die Quelle ist verlässlicher als unser Seiten-Scrape). Rein."""
    out = dict(row)
    for key in ("description", "socials", "technologies", "privacy_rating",
                "privacy_hint", "enriched"):
        value = enriched.get(key)
        if value:
            out[key] = value
    if not (out.get("email") or "").strip():
        picked = pick_email(enriched.get("emails") or [])
        if picked:
            out["email"] = picked
    return out


async def enrich_row(row: dict, *, with_contact_page: bool = True) -> dict:
    """EIN Abruf der Startseite (+ optional EINE Kontaktseite, nur wenn keine
    E-Mail gefunden wurde). Fehler → Kandidat unverändert zurück (defensiv)."""
    url = _sanitize_url(row.get("website") or "")
    if not url:
        return row
    try:
        resp = await _safe_get(url, verify=True)
        if resp.status_code >= 400:
            return row
        html = resp.text or ""
        enriched = enrichment_from_html(str(resp.url), html, dict(resp.headers))
        if with_contact_page and not (row.get("email") or "").strip() and not enriched["emails"]:
            page = contact_page_url(html, str(resp.url))
            if page:
                try:
                    r2 = await _safe_get(page, verify=True)
                    if r2.status_code < 400:
                        enriched["emails"] = extract_emails(r2.text or "")
                        if not enriched.get("socials"):
                            enriched["socials"] = extract_socials(r2.text or "")
                except Exception:  # Zusatzabruf ist optional (auch _Blocked)
                    pass
        return merge_enrichment(row, enriched)
    except Exception:  # Anreicherung darf die Suche nie killen (auch _Blocked/SSRF)
        return row


async def enrich_candidates(rows: list[dict], concurrency: int = 6) -> list[dict]:
    """Alle Kandidaten parallel anreichern (Reihenfolge bleibt erhalten)."""
    if not rows:
        return rows
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(row: dict) -> dict:
        async with sem:
            return await enrich_row(row)

    results = await asyncio.gather(*[one(r) for r in rows], return_exceptions=True)
    return [rows[i] if isinstance(r, BaseException) else r for i, r in enumerate(results)]


def enrichment_notes(row: dict) -> list[str]:
    """Notiz-Zeilen für den angelegten Lead — nur belegte Fakten, keine Wertung."""
    lines: list[str] = []
    desc = (row.get("description") or "").strip()
    if desc:
        lines.append(desc)
    techs = row.get("technologies") or []
    if techs:
        lines.append("Technik: " + ", ".join(techs))
    socials = row.get("socials") or {}
    for key, _label, _pat in SOCIAL_PATTERNS:
        if socials.get(key):
            lines.append(f"{SOCIAL_LABELS[key]}: {socials[key]}")
    return lines
