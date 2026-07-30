"""Kontaktdaten zu einem Marktradar-Eintrag: Website, E-Mail, Telefon, Geschäftsführung.

**Der Katalog liefert diese Felder nicht** — er trägt Produkt- und Marktdaten plus
die Referenz-URL. Firmenkontakte müssen also von der Herstellerseite geholt werden,
und zwar so, dass man sich auf sie verlassen kann.

**Deterministisch, nicht per Sprachmodell — und das ist die zentrale Entscheidung.**
Jeder Wert hier ist eine **wörtliche Teilzeichenfolge der abgerufenen Seite**. Damit
kann die Extraktion nichts erfinden: Sie kann etwas übersehen (dann bleibt das Feld
leer) oder eine falsche Stelle greifen (dann steht die falsche Stelle da, nicht eine
erdachte). Ein Modell könnte einen plausiblen Geschäftsführer halluzinieren, der
nirgends steht; das ist der Fehler, der hier nicht passieren darf.

Deshalb wird zu **jedem** Fund die Quell-URL und das wörtliche Zitat gespeichert
(`contact_evidence`): Ohne Beleg ist „korrekt" keine überprüfbare Aussage.

Der Preis ist eine niedrigere Trefferquote, vor allem bei der Geschäftsführung
(Impressen formulieren sie sehr unterschiedlich). Das ist der gewollte Handel:
lieber ein leeres Feld als ein falsches.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from app.services.lead_enrichment import contact_page_url, extract_emails, pick_email  # noqa: F401
from app.services.website_ai_review import extract_text
from app.services.website_analysis import _safe_get, _sanitize_url

# ---------------------------------------------------------------- Website


def vendor_origin(ref_url: str | None) -> str | None:
    """Firmenwebsite = Origin der Referenz-URL (Schema + Host, ohne Pfad).

    Die Referenz-URL zeigt immer auf eine Unterseite der Herstellerdomain — der
    Origin ist damit die Firmenseite. Dieselbe Ableitung nutzt schon die Übergabe
    in die Pipeline (`market_pipeline.vendor_website`); hier steht sie, weil die
    Anreicherung sie als Startpunkt braucht.
    """
    if not (ref_url or "").strip():
        return None
    parts = urlsplit(ref_url.strip())
    if not parts.netloc:
        return None
    return f"{parts.scheme or 'https'}://{parts.netloc}"


# ---------------------------------------------------------------- Impressum

_LINK_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
_IMPRESSUM_HINT = re.compile(r"impressum|imprint|legal-?notice", re.I)
_KONTAKT_HINT = re.compile(r"kontakt|contact", re.I)


def imprint_urls(html: str, base_url: str) -> list[str]:
    """Kandidaten-Seiten für Pflichtangaben, **Impressum zuerst**. Rein.

    Das vorhandene `lead_enrichment.contact_page_url` nimmt den ERSTEN Treffer auf
    impressum|imprint|kontakt|contact — und Footer listen „Kontakt" meist vor
    „Impressum". Live gemessen: Bei Projektron und InLoox landete man dadurch auf
    `/kontakt/`, wo keine Vertretungsangabe steht, und die Geschäftsführung blieb bei
    0 %. Für Vertretung, Rufnummer und E-Mail ist das Impressum die Pflichtseite
    (§ 5 DDG) und damit die verlässliche Quelle.

    Zusätzlich der geratene Standardpfad `/impressum`: Auf Seiten, deren Footer erst
    im Browser entsteht, ist im HTML kein Link zu finden. Ein geratener Pfad ist
    unkritisch — er liefert entweder eine echte Seite, aus der wörtlich gelesen wird,
    oder einen Fehlercode. Erfunden wird dabei nichts.
    """
    host = (urlsplit(base_url).hostname or "").lower()
    impressum, kontakt = [], []
    for href in _LINK_RE.findall(html or ""):
        if href.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolut = urljoin(base_url, href)
        if (urlsplit(absolut).hostname or "").lower() != host:
            continue
        if _IMPRESSUM_HINT.search(href):
            impressum.append(absolut)
        elif _KONTAKT_HINT.search(href):
            kontakt.append(absolut)
    geraten = [urljoin(base_url, "/impressum")] if not impressum else []
    # Reihenfolge erhalten, Dubletten raus, auf drei Versuche deckeln.
    gesehen, out = set(), []
    for u in impressum + geraten + kontakt:
        if u not in gesehen:
            gesehen.add(u)
            out.append(u)
    return out[:3]


# ---------------------------------------------------------------- Telefon

_TEL_HREF = re.compile(r"""href\s*=\s*["']tel:([^"']+)["']""", re.I)
# Nur MIT Beschriftung: eine nackte Zahlenfolge im Text ist genauso gut eine
# Umsatzangabe, eine Postleitzahl oder eine Artikelnummer.
_TEL_TEXT = re.compile(
    r"(?:Telefon|Tel\.?|Fon|Phone|Zentrale)\s*[:.]?\s*([+(]?[\d][\d\s()/.–-]{5,24})",
    re.I,
)


def _telefon_plausibel(roh: str) -> str | None:
    """Mindestens 7 Ziffern, höchstens 20 — sonst ist es keine Rufnummer.

    Sieben, weil eine deutsche Durchwahl mit Vorwahl darunter nicht vorkommt; die
    Obergrenze fängt zusammengelaufene Ziffernblöcke ab (z. B. eine Zeile, in der
    hinter der Nummer noch eine Umsatzsteuer-ID steht).
    """
    wert = " ".join((roh or "").split())
    ziffern = sum(c.isdigit() for c in wert)
    if not 7 <= ziffern <= 20:
        return None
    return wert.rstrip(" .,;:-–")[:60] or None


def extract_phone(html: str) -> tuple[str | None, str | None]:
    """Telefonnummer + wörtlicher Beleg. Rein.

    `tel:`-Links zuerst: Die sind maschinenlesbar und vom Seitenautor ausdrücklich
    als Rufnummer gekennzeichnet — die verlässlichste Quelle auf einer Webseite.
    Erst danach beschrifteter Text.
    """
    for roh in _TEL_HREF.findall(html or ""):
        wert = _telefon_plausibel(roh)
        if wert:
            return wert, f"tel:{roh.strip()}"
    text = extract_text(html or "", limit=40000)
    for m in _TEL_TEXT.finditer(text):
        wert = _telefon_plausibel(m.group(1))
        if wert:
            return wert, m.group(0).strip()[:160]
    return None, None


# ---------------------------------------------------------- Geschäftsführung

_GF_LABEL = re.compile(
    r"(?:Geschäftsführer(?:in|innen)?|Geschäftsführung|"
    r"Vertretungsberechtigt(?:e[rn]?)?|Vertreten\s+durch|"
    r"Inhaber(?:in)?|Vorstand(?:svorsitzende[rn]?)?|Vorstände)"
    r"\s*(?:\(.{0,30}?\))?\s*[:\-–]?\s*\n{0,3}\s*([^\n]{3,90})",
    re.I,
)
# Was hinter dem Namen noch mitläuft und weg muss.
_GF_SCHNITT = re.compile(r"\s*(?:\||;|·|,\s*(?:Sitz|Amtsgericht|HRB|USt)|$)", re.I)
# Zeilen, die als „Name" durchrutschen würden, es aber nicht sind.
_GF_VERBOTEN = re.compile(
    r"@|https?://|www\.|\b\d{5}\b|Amtsgericht|Registergericht|Handelsregister|"
    r"HRA?B?\b|USt|Umsatzsteuer|Datenschutz|Impressum|Telefon|Telefax|E-?Mail|"
    r"Stra(?:ße|sse)|\bStr\.|\bPostfach\b|"
    # Rechtsformen: Eine natürliche Person heißt nicht „GmbH". „Vertreten durch die
    # Muster-Verwaltungs GmbH" ist juristisch korrekt, als Anrede aber unbrauchbar —
    # und genau als Anrede wird das Feld benutzt. Lieber leer.
    r"\bGmbH\b|\bAG\b|\bKG\b|\bmbH\b|\bSE\b|\bUG\b|\be\.\s?K\.|"
    r"\bOHG\b|\bGbR\b|\be\.\s?V\.|\bLtd\b|\bInc\b",
    re.I,
)


def extract_decision_maker(html: str) -> tuple[str | None, str | None]:
    """Geschäftsführung + wörtlicher Beleg. Rein.

    Nur nach ausdrücklicher Beschriftung — im deutschen Impressum ist die
    Vertretungsangabe Pflicht (§ 5 DDG) und deshalb fast immer beschriftet. Ohne
    Label würde jeder Personenname auf der Seite in Frage kommen, auch der eines
    Ansprechpartners im Vertrieb.

    Verworfen wird, was nach Registerangabe, Adresse, Kontaktzeile oder Prosa
    aussieht: Solche Zeilen stehen im Impressum direkt neben der Vertretung und
    rutschen sonst als „Name" durch.
    """
    text = extract_text(html or "", limit=40000)
    for m in _GF_LABEL.finditer(text):
        roh = m.group(1).strip()
        # Alles ab dem ersten Trenner oder Registerhinweis abschneiden.
        schnitt = _GF_SCHNITT.search(roh)
        wert = (roh[: schnitt.start()] if schnitt and schnitt.start() > 0 else roh).strip()
        wert = wert.rstrip(" .,;:-–")
        if not 3 <= len(wert) <= 80:
            continue
        if _GF_VERBOTEN.search(wert):
            continue
        # Muss wie ein Name aussehen: mindestens zwei Wörter mit Großbuchstaben.
        namen = [w for w in re.split(r"[\s,]+", wert) if re.match(r"^[A-ZÄÖÜ]", w)]
        if len(namen) < 2:
            continue
        return wert[:255], m.group(0).strip()[:200]
    return None, None


# ------------------------------------------------------------ Mitarbeiterzahl

_MA_MUSTER = [
    # „rund 120 Mitarbeiter", „180 Beschäftigte", „50 Angestellte"
    re.compile(
        r"(?:ca\.|circa|rund|etwa|über|mehr als|knapp)?\s*(\d{1,3}(?:[. \s]\d{3})*|\d{1,5})"
        r"\s*(?:\+\s*)?(?:Mitarbeiter(?:innen|inne\w*)?|Mitarbeitende|Beschäftigte|"
        r"Angestellte|Kolleg(?:innen|en)|Mitarbeiter\*innen)",
        re.I,
    ),
    # „Team aus 40 Leuten", „Team von über 200"
    re.compile(r"Team\s+(?:aus|von)\s+(?:über|rund|ca\.|etwa)?\s*(\d{1,5})", re.I),
]

# **Der Negativfilter ist hier der eigentliche Schutz.** In diesem Datensatz sind
# ALLE 142 `kunden`-Werte Reichweiten-Angaben („~2.800 Unternehmen", „60.000+
# Anwender", „5.500 Installationen"). Genau solche Sätze stehen auch auf den
# Startseiten, und „betreut 2.800 Mitarbeiter unserer Kunden" wäre sonst eine
# Mitarbeiterzahl. Passt der Satz auf eines dieser Wörter, wird verworfen.
_MA_KONTEXT_VERBOTEN = re.compile(
    r"Kunden|Kundinnen|Nutzer|Anwender|Installationen|Lizenzen|Mandanten|"
    r"Unternehmen\s+(?:vertrauen|setzen)|Verwaltungen|Organisationen|"
    r"betreu\w+|verwalt\w+|abrechn\w+|erfass\w+",
    re.I,
)


def _satz_um(text: str, start: int, ende: int) -> str:
    """Der Satz, in dem ein Treffer steht — Kontext für den Negativfilter und Beleg."""
    links = max((text.rfind(z, 0, start) for z in ".!?\n"), default=-1)
    rechts_kandidaten = [p for p in (text.find(z, ende) for z in ".!?\n") if p != -1]
    rechts = min(rechts_kandidaten) if rechts_kandidaten else len(text)
    return text[links + 1 : rechts].strip()


def extract_employee_count(html: str) -> tuple[int | None, str | None]:
    """Mitarbeiterzahl + wörtlicher Beleg — oder (None, None). Rein.

    Absichtlich streng. Die Zahl muss unmittelbar an einem Personal-Substantiv
    hängen, und der umgebende Satz darf kein Reichweiten-Wort enthalten (s.
    `_MA_KONTEXT_VERBOTEN`). Alles über 500.000 wird verworfen: Das ist keine
    Firmengröße mehr, sondern eine Nutzerzahl, die durch den Filter gerutscht ist.
    """
    text = extract_text(html or "", limit=40000)
    for muster in _MA_MUSTER:
        for m in muster.finditer(text):
            satz = _satz_um(text, m.start(), m.end())
            if _MA_KONTEXT_VERBOTEN.search(satz):
                continue
            zahl = re.sub(r"[^\d]", "", m.group(1))
            if not zahl:
                continue
            wert = int(zahl)
            if not 1 <= wert <= 500_000:
                continue
            return wert, satz[:200]
    return None, None


# ------------------------------------------------------------------ Lauf


@dataclass
class ContactFinding:
    """Was für einen Hersteller gefunden wurde — plus Belege. Nie erfunden."""
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    decision_maker: str | None = None
    employee_count: int | None = None
    evidence: dict = field(default_factory=dict)
    error: str | None = None

    def hat_daten(self) -> bool:
        return any([self.website, self.email, self.phone, self.decision_maker,
                    self.employee_count])


def _beleg(evidence: dict, feld: str, url: str, zitat: str | None) -> None:
    evidence[feld] = {"quelle": url, "zitat": zitat} if zitat else {"quelle": url}


async def fetch_contacts(ref_url: str | None) -> ContactFinding:
    """Startseite (+ Impressum) einer Herstellerdomain abrufen und auslesen.

    Zwei Abrufe höchstens: Startseite immer, Impressum nur wenn dort etwas fehlt.
    Das Impressum ist die bessere Quelle für Vertretung und Rufnummer (Pflichtangaben),
    die Startseite die bessere für die Mitarbeiterzahl (steht im „Über uns"-Ton).

    Fehler sind normal — 5 der 142 Referenz-URLs waren schon beim Katalogbau nicht
    erreichbar. Ein Fehlschlag liefert `error`, nie einen geratenen Wert.
    """
    f = ContactFinding()
    origin = vendor_origin(ref_url)
    if not origin:
        f.error = "keine Referenz-URL"
        return f
    url = _sanitize_url(origin)
    if not url:
        f.error = "Adresse nicht verwendbar"
        return f

    try:
        resp = await _safe_get(url, verify=True)
    except Exception as exc:                      # auch _Blocked (SSRF-Schutz)
        f.error = f"Startseite nicht erreichbar ({type(exc).__name__})"
        return f
    if resp.status_code >= 400:
        f.error = f"Startseite antwortet {resp.status_code}"
        return f

    start_url = str(resp.url)
    start_html = resp.text or ""
    # Die Website gilt als belegt, sobald die Seite wirklich geantwortet hat.
    f.website = f"{urlsplit(start_url).scheme}://{urlsplit(start_url).netloc}"
    _beleg(f.evidence, "website", start_url, None)

    def auslesen(html: str, quelle: str) -> None:
        if not f.email:
            mail = pick_email(extract_emails(html))
            if mail:
                f.email = mail
                _beleg(f.evidence, "email", quelle, mail)
        if not f.phone:
            tel, beleg = extract_phone(html)
            if tel:
                f.phone = tel
                _beleg(f.evidence, "phone", quelle, beleg)
        if not f.decision_maker:
            gf, beleg = extract_decision_maker(html)
            if gf:
                f.decision_maker = gf
                _beleg(f.evidence, "decision_maker", quelle, beleg)
        if not f.employee_count:
            anzahl, beleg = extract_employee_count(html)
            if anzahl:
                f.employee_count = anzahl
                _beleg(f.evidence, "employee_count", quelle, beleg)

    auslesen(start_html, start_url)

    # Pflichtangaben-Seiten der Reihe nach, solange etwas fehlt. Höchstens zwei
    # Zusatzabrufe je Hersteller — das reicht, um Impressum ODER Kontakt zu treffen,
    # ohne die Seite mit Anfragen zu belegen.
    versuche = 0
    for seite in imprint_urls(start_html, start_url):
        if f.email and f.phone and f.decision_maker:
            break
        if versuche >= 2:
            break
        versuche += 1
        try:
            r2 = await _safe_get(seite, verify=True)
            if r2.status_code < 400:
                auslesen(r2.text or "", str(r2.url))
        except Exception:
            continue                              # Zusatzabruf ist optional
    return f
