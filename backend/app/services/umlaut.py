"""Transliterierte Umlaute zurückverwandeln — regelbasiert mit Ausnahmeliste.

**Was das Problem NICHT ist.** Es gibt keinen Kodierungsfehler: In der ganzen Datenbank
steht kein einziges Mojibake-Zeichen (`Ã¤`, `â€`), und die geernteten Firmennamen sowie
die Lösungsbausteine tragen korrekte Umlaute. Betroffen sind die **importierten
Katalogtexte**: Das Recherche-Repo schreibt `ae/oe/ue` statt `ä/ö/ü` — gemessen in 139
von 142 Produkten.

**Warum eine blinde Regel Text zerstört.** In denselben Texten stehen Wörter, die diese
Buchstabenfolgen völlig zu Recht tragen: `manuell`, `aktuell`, `neue`, `Steuerberatung`,
`Lead-Quelle`, `Betreuung`, `Koeffizient`. Ein pauschales `ue → ü` macht daraus
„manüll" und „Lead-Qülle". Deshalb: Regel **plus** Ausnahmeliste, und die Liste ist aus
den echten Daten gebaut (alle 618 Wörter mit `ae|oe|ue` einmal durchgesehen), nicht
geraten.

**`ss → ß` wird NICHT angefasst.** Dort ist die Umkehrung noch mehrdeutiger („dass",
„Prozess", „Adresse", „Messung" sind korrekt), und im gemessenen Bestand gibt es kein
einziges betroffenes Wort. Ein Riegel, der nichts repariert, aber Text kaputtmachen
kann, gehört nicht in den Code.

**Wo das angewandt wird:** im Import (`market_import`), damit jeder künftige Katalog
korrekt landet, und einmalig über den Bestand. Eine Implementierung, beide Wege — sonst
überschriebe der nächste Import die Korrektur wieder.
"""
from __future__ import annotations

import re

# Wörter (klein geschrieben), in denen ae/oe/ue KORREKT sind. Aus den 618 im Bestand
# gemessenen Kandidaten durchgesehen und um die naheliegenden deutschen Fälle ergänzt,
# die dort noch fehlen könnten.
#
# Verglichen wird gegen den kleingeschriebenen Wortstamm mit `startswith`, damit
# Beugungen und Zusammensetzungen mitkommen („neue", „neuer", „neuesten";
# „Steuerberatung", „Steuerungssystem").
AUSNAHMEN_ANFANG = (
    # -ue- als reguläres „u + e"
    "neu", "steuer", "feuer", "treu", "reue", "abenteuer", "erneuer", "betreu",
    "beteuer", "queue", "quelle", "quell", "manuell", "aktuell", "individuell",
    "eventuell", "visuell", "sexuell", "konzeptuell", "intellektuell", "graduell",
    "residuell", "duell", "ritual", "aktualis", "manual", "annuell",
    # -oe-
    "poesie", "poet", "koexist", "koeffizient", "koedukation", "boeing", "goethe",
    "koordin", "koaliti", "koautor",
    # -ae-
    "aerosol", "aerodynam", "aerob", "aero", "michael", "raphael", "israel",
    "praesidium",   # Eigenname-Schreibweise im Bestand belassen
)

# Zusammensetzungen, in denen die Folge über eine Wortgrenze läuft und die Regel
# sonst zuschlagen würde. Ganzes Wort, kleingeschrieben.
AUSNAHMEN_GANZ = {
    "lead-quelle", "leadquelle", "co-autor",
}

_UMLAUT = (("Ae", "Ä"), ("Oe", "Ö"), ("Ue", "Ü"), ("ae", "ä"), ("oe", "ö"), ("ue", "ü"))
# Wort = Buchstaben, Ziffern, Binde- und Schrägstriche, Punkte im Wortinneren.
_WORT = re.compile(r"[0-9A-Za-zÄÖÜäöüß][0-9A-Za-zÄÖÜäöüß.\-/]*")


def ist_ausnahme(wort: str) -> bool:
    """Trägt das Wort `ae/oe/ue` zu Recht? Rein."""
    klein = wort.lower().strip(".,;:!?")
    if klein in AUSNAHMEN_GANZ:
        return True
    # Teile einer Zusammensetzung getrennt prüfen: „Lead-Quelle" → „lead", „quelle".
    teile = [t for t in re.split(r"[-/.]", klein) if t]
    return any(
        t.startswith(a) or a.startswith(t) and len(t) >= 4
        for t in teile for a in AUSNAHMEN_ANFANG
    ) or any(klein.startswith(a) for a in AUSNAHMEN_ANFANG)


def wort_zurueck(wort: str) -> str:
    """Ein Wort zurückverwandeln — oder unverändert lassen. Rein."""
    if not re.search(r"[AaOoUu]e", wort):
        return wort
    if ist_ausnahme(wort):
        return wort
    out = wort
    for von, nach in _UMLAUT:
        out = out.replace(von, nach)
    return out


def entschluessele(text: str | None) -> str | None:
    """Transliterierte Umlaute in einem Text zurückverwandeln. Rein.

    Arbeitet **wortweise**, nicht auf dem ganzen Text: Nur so kann die Ausnahmeliste
    greifen. Nicht-Wortzeichen (Satzzeichen, Klammern, Zahlenformate) bleiben, wie sie
    sind.
    """
    if not text:
        return text
    return _WORT.sub(lambda m: wort_zurueck(m.group(0)), text)


def entschluessele_liste(werte: list | None) -> list | None:
    """Dasselbe für eine Liste von Zeichenketten (JSON-Felder im Katalog). Rein."""
    if not werte:
        return werte
    return [entschluessele(v) if isinstance(v, str) else v for v in werte]
