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

# Ganze Wörter, bei denen die Folge über eine Wortgrenze läuft und keine
# Positionsregel greift.
AUSNAHMEN_GANZ = {"lead-quelle", "leadquelle", "co-autor"}

_UMLAUT = {"ae": "ä", "oe": "ö", "ue": "ü", "Ae": "Ä", "Oe": "Ö", "Ue": "Ü"}
# Wort = Buchstaben, Ziffern, Binde- und Schrägstriche, Punkte im Wortinneren.
_WORT = re.compile(r"[0-9A-Za-zÄÖÜäöüß][0-9A-Za-zÄÖÜäöüß.\-/]*")
_PAAR = re.compile(r"[AaOoUu]e")


def _geschuetzte_stellen(wort: str) -> set[int]:
    """Zeichenpositionen, die zu einem Ausnahme-Wortstamm gehören. Rein.

    **Positionsgenau, nicht wortweise — und das ist der Kern.** Die erste Fassung
    übersprang das GANZE Wort, sobald ein Ausnahmestamm passte. In einer
    Zusammensetzung kann aber ein `ue` zu Recht stehen und ein `ae` später falsch
    sein: `Betreuungskraefte` (→ Betreuungskräfte) und
    `Aktualisierungsvorschlaege` (→ Aktualisierungsvorschläge) blieben dadurch
    unkorrigiert. Beim Durchsehen der 623 echten Katalogwörter aufgefallen.
    """
    klein = wort.lower()
    stellen: set[int] = set()
    for stamm in AUSNAHMEN_ANFANG:
        start = klein.find(stamm)
        while start != -1:
            stellen.update(range(start, start + len(stamm)))
            start = klein.find(stamm, start + 1)
    return stellen


def wort_zurueck(wort: str) -> str:
    """Ein Wort zurückverwandeln — Folge für Folge, Ausnahmen positionsgenau. Rein."""
    if not _PAAR.search(wort):
        return wort
    if wort.lower().strip(".,;:!?") in AUSNAHMEN_GANZ:
        return wort
    geschuetzt = _geschuetzte_stellen(wort)
    aus: list[str] = []
    i = 0
    while i < len(wort):
        paar = wort[i:i + 2]
        if paar in _UMLAUT and i not in geschuetzt and i + 1 not in geschuetzt:
            aus.append(_UMLAUT[paar])
            i += 2
        else:
            aus.append(wort[i])
            i += 1
    return "".join(aus)


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
