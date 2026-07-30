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

Deshalb: Form erkennen, ernten, und die Ernte **inhaltlich** prüfen.

**Nicht über die Menge.** Der erste Entwurf verglich die Erntemenge mit `refs` aus
dem Katalog — und fiel am echten Lauf in beide Richtungen um: Bei ADITO gingen 49
Funde als „plausibel" durch, obwohl ALLE Menüpunkte waren („Kontaktmanagement",
„Vertrieb", „Preise"); bei SER Group wurden 173 als „unplausibel viele" verworfen,
obwohl es echte Konzerne waren (Deutsche Bahn, Allianz, Eli Lilly, Würth, DHL).
Die Menge sagt nichts darüber, OB es Firmen sind. Entscheidend ist der Anteil an
Namen mit **Rechtsform oder öffentlichem Träger** (s. `ist_kundenliste`): bei einer
Kundenliste hoch, bei Navigation null — die Trennung ist scharf, nicht knapp.
`refs` bleibt als Angabe zur Abdeckung nützlich, ist aber kein Tor mehr.

Gelesen werden **nur Firmennamen und -Websites** — keine Personendaten.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

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
# Menü- und Produktbegriffe. Am echten Fall gelernt: Auf der ADITO-Seite waren ALLE
# 49 „Namen" Navigation („Kontaktmanagement", „Vertrieb", „Preise", „CRM"), und die
# baramundi-Ernte begann mit sieben Menüpunkten.
_NAVIGATION = re.compile(
    r"^(?:lösungen|loesungen|lÖsungen|produkte|leistungen|services?|service|"
    r"branchen|referenzen|kunden|über\s?uns|ueber\s?uns|unternehmen|team|"
    r"karriere|jobs|kontakt|support|downloads?|preise|pricing|tarife|blog|news|"
    r"events?|webinare?|schulungen|seminare|academy|akademie|übersicht|uebersicht|"
    r"vertrieb|marketing|collaboration|crm|srm|erp|dms|ecm|cloud|schnittstellen|"
    r"customizing|vorteile|funktionen|features|module|integration|api|"
    r"künstliche\s+intelligenz|kuenstliche\s+intelligenz|ki|datenschutz|"
    r"impressum|agb|newsletter|mediathek|presse|partner|partnerprogramm|"
    r"healthcare|industrie|handel|banken|versicherungen|öffentlicher\s+dienst|"
    r"anmelden|login|demo|testen|jetzt\s+\w+|mehr\s+erfahren|home|startseite)$",
    re.I,
)
# „Logo Siemens", „Siemens Logo", „Referenz: Stadt X" → der Name bleibt übrig.
_ABSCHNEIDEN = re.compile(
    r"^(?:logo|logos|referenz|referenzen|kunde|kunden|kundenlogo|partner|bild)"
    r"[\s:_-]+|[\s:_-]+(?:logo|logos|referenz|kundenlogo)$", re.I)


def saeubere_namen(roh: str) -> str | None:
    """Ein Kandidat → Firmenname oder None. Rein.

    Schneidet die üblichen Beiwörter ab („Logo Siemens" → „Siemens") und wirft alles
    weg, was nach Deko, Satz oder Fragment aussieht.

    Zwei Dinge, die erst am echten Lauf auffielen:

      · **Entities dekodieren.** Attributwerte kommen kodiert aus dem HTML — ohne
        Dekodierung landete „Spandauer Velours GmbH &amp; Co. KG" so in der Datenbank.
      · **„<Produkt> Logo <Firma>" abschneiden.** HOPPE beschriftet jedes Kundenlogo
        mit „Wartungsplaner Logo BDL Untermain GmbH"; der Produktname stand damit vor
        jedem der 1226 Namen.
    """
    import html as html_mod
    name = " ".join(html_mod.unescape(roh or "").split())
    # Alles vor einem eingebetteten „Logo" verwerfen — davor steht der Produkt- oder
    # Herstellername des Seitenbetreibers, danach der Kunde.
    m = re.search(r"\bLogos?\b[\s:_-]*(.+)$", name, re.I)
    if m and len(m.group(1).strip()) >= 3:
        name = m.group(1).strip()
    name = _ABSCHNEIDEN.sub("", name).strip(" ·–—-:|")
    if not 3 <= len(name) <= 70:
        return None
    if _NUR_DEKO_WORT.match(name) or _DEKO.match(name) or _NAVIGATION.match(name):
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


def hat_firmen_marker(name: str) -> bool:
    """Trägt der Name einen HARTEN Firmenbeleg — Rechtsform oder öffentlicher Träger?

    Das ist das einzige inhaltliche Merkmal, an dem sich eine Kundenliste von einer
    Navigationsleiste unterscheiden lässt.
    """
    return bool(_RECHTSFORM.search(name) or _OEFFENTLICH.match(name))


def marker_anteil(namen: list[str]) -> float:
    """Anteil der Namen mit hartem Firmenbeleg. Rein."""
    if not namen:
        return 0.0
    return sum(1 for n in namen if hat_firmen_marker(n)) / len(namen)


MIN_NAMEN = 8


def ohne_seitenrauschen(namen: list[str], rauschen: set[str]) -> list[str]:
    """Alles abziehen, was auch auf einer ANDEREN Seite derselben Domain steht. Rein.

    **Das ist das tragende Signal.** Navigation, Produktnamen und Auszeichnungslogos
    stehen auf jeder Seite der Domain; Kundenlogos nur im Referenzverzeichnis. Die
    Differenz zur Startseite trennt beides strukturell — ohne Blockliste, ohne
    Wörterbuch, ohne DOM-Analyse.

    Nötig wurde es, weil ein inhaltliches Tor allein in eine Richtung falsch lag:
    Der Anteil an Namen mit Rechtsform trennt Mittelstands-Listen gut von Navigation,
    bestraft aber gerade die hochwertigste Sorte Liste — große Marken tragen keine
    Rechtsform („GLS", „Helvetia", „Randstad", „Eli Lilly", „DHL Express"). Die
    SER-Group-Ernte mit 173 echten Konzernen kam damit auf 24 % und wäre verworfen
    worden.
    """
    return [n for n in namen if re.sub(r"[^a-z0-9]", "", n.lower()) not in rauschen]


def rauschschluessel(namen: list[str]) -> set[str]:
    """Namen zu Vergleichsschlüsseln — für `ohne_seitenrauschen`. Rein."""
    return {re.sub(r"[^a-z0-9]", "", n.lower()) for n in namen if n}


def ist_kundenliste(namen: list[str]) -> tuple[bool, str]:
    """Ist die Ernte AS GANZES eine Kundenliste? Rein.

    Nach dem Abzug des Seitenrauschens ist die Menge wieder ein brauchbares Kriterium:
    Was übrig bleibt, ist per Konstruktion seitenspezifischer Inhalt — auf einer
    Referenzseite also die Kunden. Der Anteil an Rechtsformen wird nur noch **berichtet**,
    nicht mehr als Tor benutzt (s. `ohne_seitenrauschen`, warum er als Tor scheitert).

    Die frühere Zähl-Prüfung gegen `refs` aus dem Katalog ist ebenfalls weg: Sie ließ
    ADITOs 49 Menüpunkte durch („plausibel bei 100 erwarteten") und verwarf SERs 173
    Konzerne („unplausibel viele").
    """
    if len(namen) < MIN_NAMEN:
        return False, f"zu wenig ({len(namen)})"
    return True, f"{len(namen)} Namen, {marker_anteil(namen):.0%} mit Rechtsform"


def ohne_eigenen_namen(namen: list[str], vendor: str) -> list[str]:
    """Den Hersteller selbst aus seiner Kundenliste nehmen. Rein.

    Auf der Vertec-Seite stand „Vertec Gruppe" als erster „Kunde" — das eigene Logo
    in derselben Wand. Verglichen wird über das erste Namenswort, damit auch
    „Vertec AG" und „Vertec Gruppe" fallen.
    """
    kern = re.sub(r"[^a-z0-9]", "", (vendor or "").split()[0].lower()) if vendor.strip() else ""
    if not kern or len(kern) < 4:
        return namen
    return [n for n in namen
            if kern not in re.sub(r"[^a-z0-9]", "", n.lower())]


def ernte_aus_html(
    html: str, basis: str, refs: int, vendor: str = "",
    rauschen: set[str] | None = None,
) -> Ernte:
    """Form erkennen, ernten, inhaltlich prüfen. Rein — kein Netz.

    Reihenfolge der Formen ist Absicht: Verlinkte Logos zuerst (Name UND Website),
    dann die Logo-Wand, dann die Textliste. Genommen wird die **größte** Ernte, die
    als Kundenliste durchgeht — nicht die erste: Eine Seite kann fünf verlinkte
    Partnerlogos UND eine Wand mit 200 Kunden tragen.
    """
    e = Ernte()
    verlinkt = ernte_verlinkt(html, basis)
    versuche = [
        ("verlinkt", [n for n, _ in verlinkt], {n: w for n, w in verlinkt if w}),
        ("logowand", ernte_logowand(html), {}),
        ("textliste", ernte_textliste(html), {}),
    ]
    treffer, beste_verworfen = [], None
    for form, namen, websites in versuche:
        sauber = ohne_eigenen_namen(dedupe(namen), vendor)
        if rauschen:
            sauber = ohne_seitenrauschen(sauber, rauschen)
        ok, grund = ist_kundenliste(sauber)
        if ok:
            treffer.append((len(sauber), form, sauber, websites, grund))
        elif beste_verworfen is None or len(sauber) > beste_verworfen[0]:
            beste_verworfen = (len(sauber), form, grund)
    if treffer:
        treffer.sort(reverse=True)
        _, e.form, e.namen, e.websites, e.verdikt = treffer[0]
        e.roh_anzahl = len(e.namen)
        if refs > 0:
            e.verdikt += f" · {len(e.namen)} von erwarteten {refs}"
        return e
    if beste_verworfen:
        e.roh_anzahl, e.form, e.verdikt = (
            beste_verworfen[0], beste_verworfen[1], f"verworfen: {beste_verworfen[2]}")
    return e
