"""Referenzverzeichnisse auslesen: die Kunden eines Herstellers als Lead-Kandidaten.

**Das ist der eigentliche Zweck des Marktradars.** Zum Lead wird nicht der Hersteller,
sondern wer seine Software *einsetzt*: „Sie arbeiten mit [Software X] — ich baue
[Baustein N] darauf." Genau das Muster von bcsbook (Baustein 10, Zeiterfassungs-
Assistent, auf Projektron BCS). Die 142 Einträge zeigen auf 8.664 solche Firmen.

**Es gibt kein einheitliches Verfahren.** An sechs Verzeichnissen gemessen:

    AEB SE       refs=200   259 img-alt      → Logo-Wand, alt-Texte sind die Namen
    InLoox       refs=200   164 img-alt      → Logo-Wand
    HOPPE        refs=200  1575 img-alt      → viel zu viele, Deko dabei
    SOMACOS      refs=200     3 img-alt      → Namen stehen im Text (Kommunen)
    Projektron   refs=267    49 img-alt      → Übersicht verlinkt Fallstudien
    DocuWare     refs=245                    → Referenz-URL leitet um, Liste weg

Deshalb: Form erkennen, dann die passende Ernte — und **jede Ernte gegen `refs`
prüfen**. Dieser Prüfstein ist das Besondere an diesem Datensatz: Der Katalog sagt,
wie viele Firmen dort stehen sollen. 259 gefunden bei 200 erwartet ist plausibel,
1575 bei 200 ist Rauschen. Ohne dieses Tor wäre „keine erfundenen Daten" nicht zu
halten, weil eine Seite beliebig viel Deko enthalten kann.

Gelesen werden **nur Firmennamen und -Websites** — keine Personendaten.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

# ---------------------------------------------------------------- robots.txt

_UA_ZEILE = re.compile(r"^\s*user-agent\s*:\s*(.+?)\s*$", re.I | re.M)
_REGEL = re.compile(r"^\s*(allow|disallow)\s*:\s*(\S*)\s*$", re.I | re.M)


def robots_erlaubt(robots_txt: str | None, pfad: str) -> bool:
    """Darf `pfad` laut robots.txt für `*` geholt werden? Rein.

    Bewusst minimal: Nur der `*`-Block, längste passende Regel gewinnt (so steht es
    im Standard). Keine robots.txt und kein `*`-Block heißen erlaubt — Abwesenheit
    einer Regel ist keine Verbotsregel.
    """
    if not (robots_txt or "").strip():
        return True
    zeilen = robots_txt.splitlines()
    im_stern_block = False
    regeln: list[tuple[str, str]] = []
    for zeile in zeilen:
        ua = _UA_ZEILE.match(zeile)
        if ua:
            im_stern_block = ua.group(1).strip() == "*"
            continue
        if not im_stern_block:
            continue
        r = _REGEL.match(zeile)
        if r:
            regeln.append((r.group(1).lower(), r.group(2)))
    treffer = [(len(muster), art) for art, muster in regeln
               if muster and pfad.startswith(muster)]
    if not treffer:
        return True
    treffer.sort(reverse=True)
    return treffer[0][1] == "allow"


# ------------------------------------------------------- Firmenname-Erkennung

_RECHTSFORM = re.compile(
    r"\b(?:GmbH|gGmbH|AG|KGaA|KG|OHG|GbR|mbH|SE|UG|Ltd|Inc|LLC|BV|B\.V\.|"
    r"N\.V\.|S\.A\.|S\.p\.A\.|AB|A/S|Oy|Sp\.\s?z\s?o\.o\.|"
    r"e\.\s?V\.|e\.\s?K\.|e\.\s?G\.|eG)\b",
)
_OEFFENTLICH = re.compile(
    r"^(?:Stadt|Stadtwerke|Gemeinde|Samtgemeinde|Verbandsgemeinde|Landkreis|Kreis|"
    r"Bezirk|Freistaat|Land\b|Bundes\w+|Landes\w+|Universität|Universitäts\w+|"
    r"Uni\b|Hochschule|Fachhochschule|Klinik\w*|Krankenhaus|Universitätsklinik\w*|"
    r"Amt\b|Ministerium|Regierungspräsidium|Bundesamt|Bundesanstalt|"
    r"Verband|Verein|Stiftung|Kammer|Handwerkskammer|IHK|Sparkasse|Volksbank|"
    r"Raiffeisenbank|Diakonie|Caritas|DRK|Johanniter|Malteser|AWO)\b",
    re.I,
)

# Was auf einer Marketingseite als `alt` steht, aber keine Kundenfirma ist.
_DEKO = re.compile(
    r"^(?:logo|icon|symbol|pfeil|arrow|play|pause|close|schließen|menü|menu|"
    r"suche|search|banner|hero|slider|avatar|platzhalter|placeholder|"
    r"bild|foto|image|grafik|illustration|screenshot|hintergrund|background|"
    r"stern|star|zitat|quote|flagge|flag|deutsch|english|de|en|next|prev|"
    r"weiter|zurück|mehr|download|pdf|youtube|linkedin|xing|facebook|twitter|"
    r"instagram|cookie|newsletter|kontakt|karriere|impressum)\b",
    re.I,
)
_NUR_DEKO_WORT = re.compile(r"^(?:logo|referenz|kunde|kundenlogo|partner)$", re.I)
# „Logo Siemens", „Siemens Logo", „Referenz: Stadt X" → der Name bleibt übrig.
_ABSCHNEIDEN = re.compile(
    r"^(?:logo|logos|referenz|referenzen|kunde|kunden|kundenlogo|partner|bild)"
    r"[\s:_-]+|[\s:_-]+(?:logo|logos|referenz|kundenlogo)$", re.I)


def saeubere_namen(roh: str) -> str | None:
    """Ein Kandidat → Firmenname oder None. Rein.

    Schneidet die üblichen Beiwörter ab („Logo Siemens" → „Siemens") und wirft alles
    weg, was nach Deko, Satz oder Fragment aussieht.
    """
    name = " ".join((roh or "").split())
    name = _ABSCHNEIDEN.sub("", name).strip(" ·–—-:|")
    if not 3 <= len(name) <= 70:
        return None
    if _NUR_DEKO_WORT.match(name) or _DEKO.match(name):
        return None
    if "@" in name or "http" in name.lower():
        return None
    # Ein ganzer Satz ist kein Firmenname.
    if len(name.split()) > 7 or name.endswith((".", "!", "?")) and len(name.split()) > 4:
        return None
    if not re.search(r"[A-Za-zÄÖÜäöüß]", name):
        return None
    return name


def ist_firmenname(name: str, *, streng: bool) -> bool:
    """Sieht das nach einer Firma oder Behörde aus? Rein.

    `streng=True` verlangt einen harten Beleg — Rechtsform oder öffentlicher Träger.
    Das ist die Stufe für Textlisten, wo jede Zeile ein Kandidat ist und ein Irrtum
    sonst massenhaft passiert.

    `streng=False` lässt zusätzlich „zwei bis fünf großgeschriebene Wörter" zu. Das
    ist die Stufe für Logo-Wände: Dort ist der `alt`-Text vom Seitenautor als
    Firmenbezeichnung gesetzt, der Kontext also schon ein Beleg.
    """
    if _RECHTSFORM.search(name) or _OEFFENTLICH.match(name):
        return True
    if streng:
        return False
    woerter = name.split()
    if not 1 <= len(woerter) <= 5:
        return False
    gross = sum(1 for w in woerter if re.match(r"^[A-ZÄÖÜ0-9]", w))
    return gross >= max(1, len(woerter) - 1)


# ------------------------------------------------------------------ Ernte

_IMG = re.compile(r"<img\b[^>]*>", re.I)
_ALT = re.compile(r"""\balt\s*=\s*["']([^"']*)["']""", re.I)
_TITLE = re.compile(r"""\btitle\s*=\s*["']([^"']*)["']""", re.I)
_LI = re.compile(r"<li\b[^>]*>(.*?)</li>", re.I | re.S)
_TD = re.compile(r"<td\b[^>]*>(.*?)</td>", re.I | re.S)
_TAGS = re.compile(r"<[^>]+>")
_A = re.compile(r"""<a\b[^>]*href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""", re.I | re.S)


def _text(fragment: str) -> str:
    import html as html_mod
    return " ".join(html_mod.unescape(_TAGS.sub(" ", fragment or "")).split())


def ernte_logowand(html: str) -> list[str]:
    """Firmennamen aus `alt`/`title` der Bilder. Rein."""
    out: list[str] = []
    for tag in _IMG.findall(html or ""):
        for muster in (_ALT, _TITLE):
            m = muster.search(tag)
            if not m:
                continue
            name = saeubere_namen(m.group(1))
            if name and ist_firmenname(name, streng=False):
                out.append(name)
                break
    return out


def ernte_textliste(html: str) -> list[str]:
    """Firmennamen aus Listen- und Tabellenzellen. Rein, strenge Prüfung."""
    out: list[str] = []
    for muster in (_LI, _TD):
        for fragment in muster.findall(html or ""):
            name = saeubere_namen(_text(fragment))
            if name and ist_firmenname(name, streng=True):
                out.append(name)
    return out


def ernte_verlinkt(html: str, basis: str) -> list[tuple[str, str | None]]:
    """(Name, Website) aus Links auf FREMDE Domains — Logo-Wände verlinken oft
    direkt zum Kunden. Das ist der wertvollste Fund: Name plus Website in einem.
    Rein."""
    eigen = (urlsplit(basis).hostname or "").lower().removeprefix("www.")
    out: list[tuple[str, str | None]] = []
    for href, inner in _A.findall(html or ""):
        if not href.startswith("http"):
            continue
        host = (urlsplit(href).hostname or "").lower().removeprefix("www.")
        if not host or host == eigen or host.endswith(f".{eigen}") or eigen.endswith(f".{host}"):
            continue
        # Name aus dem Linktext oder dem alt des enthaltenen Bildes.
        kandidat = _text(inner)
        if not kandidat:
            m = _ALT.search(inner)
            kandidat = m.group(1) if m else ""
        name = saeubere_namen(kandidat)
        if name and ist_firmenname(name, streng=False):
            out.append((name, f"{urlsplit(href).scheme}://{urlsplit(href).netloc}"))
    return out


def dedupe(namen: list[str]) -> list[str]:
    """Groß-/Kleinschreibung und Mehrfachnennung raus, Reihenfolge bleibt. Rein."""
    gesehen, out = set(), []
    for n in namen:
        k = re.sub(r"[^a-z0-9]", "", n.lower())
        if k and k not in gesehen:
            gesehen.add(k)
            out.append(n)
    return out


# --------------------------------------------------------- Plausibilitätstor

@dataclass
class Ernte:
    form: str = "unbekannt"
    namen: list[str] = field(default_factory=list)
    websites: dict = field(default_factory=dict)
    roh_anzahl: int = 0
    verdikt: str = ""
    error: str | None = None


def plausibel(gefunden: int, refs: int) -> tuple[bool, str]:
    """Passt die Erntemenge zur erwarteten Zahl aus dem Katalog? Rein.

    **Das Tor, das die Zusage „keine erfundenen Daten" trägt.** Eine Marketingseite
    enthält beliebig viel Deko; ohne Erwartungswert wäre nicht entscheidbar, ob 1575
    Funde eine reiche Liste oder Müll sind. `refs` liefert den Erwartungswert.

    Untergrenze 30 %: Teil-Listen (erste Seite einer Paginierung) sind brauchbar.
    Obergrenze 160 %: etwas Luft für Logos, die mehrfach im Markup stehen.
    """
    if gefunden < 3:
        return False, f"zu wenig ({gefunden})"
    if refs <= 0:
        return False, "keine Erwartung im Katalog"
    if gefunden > refs * 1.6:
        return False, f"unplausibel viele ({gefunden} bei erwarteten {refs})"
    if gefunden < refs * 0.3:
        return True, f"Teilmenge ({gefunden} von erwarteten {refs})"
    return True, f"plausibel ({gefunden} von erwarteten {refs})"


def ernte_aus_html(html: str, basis: str, refs: int) -> Ernte:
    """Form erkennen, ernten, gegen `refs` prüfen. Rein — kein Netz.

    Reihenfolge der Formen ist Absicht: Verlinkte Logos zuerst (Name UND Website),
    dann die Logo-Wand, dann die Textliste. Genommen wird die erste Form, die das
    Plausibilitätstor besteht.
    """
    e = Ernte()
    versuche = [
        ("verlinkt", [n for n, _ in ernte_verlinkt(html, basis)],
         {n: w for n, w in ernte_verlinkt(html, basis) if w}),
        ("logowand", ernte_logowand(html), {}),
        ("textliste", ernte_textliste(html), {}),
    ]
    beste = None
    for form, namen, websites in versuche:
        sauber = dedupe(namen)
        ok, grund = plausibel(len(sauber), refs)
        if ok:
            e.form, e.namen, e.websites = form, sauber, websites
            e.roh_anzahl = len(namen)
            e.verdikt = grund
            return e
        if beste is None or len(sauber) > len(beste[1]):
            beste = (form, sauber, grund)
    if beste:
        e.form, e.namen, e.verdikt = beste[0], [], f"verworfen: {beste[2]}"
        e.roh_anzahl = len(beste[1])
    return e
