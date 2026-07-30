"""Wie lohnend ist ein Referenzkunde? — offengelegte Bewertung, keine Blackbox.

**Was hier NICHT behauptet wird.** Gespeichert ist je Firma der Name, die Quell-URL
und bei einem Bruchteil eine Website — keine Größe, kein Umsatz, keine eigene Branche.
„Lukrativ" im kaufmännischen Sinn lässt sich daraus nicht berechnen. Diese Bewertung
ordnet nach den Signalen, die **tatsächlich vorliegen**, und legt jeden Bestandteil
offen, damit man ihr widersprechen kann.

Die vier Bestandteile, nach Aussagekraft:

  1. **Mehrfachnutzung** — die Firma steht im Referenzverzeichnis mehrerer Hersteller.
     Das einzige echte Pro-Kunde-Signal im Datensatz: mehr Systeme heißt mehr
     Schnittstellen und Integrationsschmerz, und es gibt zwei Gesprächseinstiege
     statt einem. Deshalb das höchste Gewicht.
  2. **Passender Baustein** — für die genutzte Software liegt eine Aufsatzlösung
     bereit (`market_bausteine.catalog_ids`). Ohne sie gibt es nichts zu verkaufen,
     egal wie attraktiv die Firma wäre.
  3. **Produkt-Score** des Herstellers aus der Recherche. Beschreibt das *Umfeld*
     (Marktplatz, Regulatorik, Integrationsaufwand), nicht die Firma — deshalb
     abgeschwächt.
  4. **Website bekannt** — kein Qualitäts-, sondern ein Ansprechbarkeitssignal: ohne
     sie steht vor dem ersten Kontakt eine Handrecherche. Kleines Gewicht.

**Der Organisationstyp ist bewusst NICHT Teil der Formel.** Ob ein Klinikum lohnender
ist als ein Maschinenbauer im Mittelstand, hängt am Angebot und am Vertriebsweg — das
kann diese Datei nicht wissen. Er wird als Kennzeichen und Filter geliefert, damit die
Entscheidung dort bleibt, wo sie hingehört.
"""
from __future__ import annotations

import re

# Gewichte. Summe der Höchstwerte = 100, damit der Score ohne Umrechnung lesbar ist.
W_MEHRFACH_JE_SYSTEM = 35      # ab dem zweiten System
W_MEHRFACH_MAX = 55
W_BAUSTEIN = 20
W_PRODUKT_MAX = 20             # Produkt-Score 0–100 → 0–20
W_WEBSITE = 5


ORG_TYPEN = ("oeffentlich", "konzern", "mittelstand", "unbekannt")

_OEFFENTLICH = re.compile(
    r"^(?:Stadt|Stadtwerke|Gemeinde|Samtgemeinde|Verbandsgemeinde|Landkreis|Kreis|"
    r"Bezirk|Freistaat|Land\b|Bundes\w+|Landes\w+|Universität|Universitäts\w+|"
    r"Uni\b|Hochschule|Fachhochschule|Klinik\w*|Krankenhaus|Kreiskrankenhaus|"
    r"Amt\b|Ministerium|Regierungspräsidium|Bundesamt|Bundesanstalt|Deutsche Rentenv|"
    r"Verband|Verein|Stiftung|Kammer|Handwerkskammer|IHK|Sparkasse|Volksbank|"
    r"Raiffeisenbank|Diakonie|Caritas|DRK|Johanniter|Malteser|AWO|AOK|Barmer|"
    r"Techniker Krankenkasse|Berufsgenossenschaft)\b",
    re.I,
)
# Konzernhinweise: Holding-Strukturen und internationale Rechtsformen. Eine reine
# Größenaussage ist das nicht — ein Signal für „mehr als ein Standort" schon.
# **Kein `\b` hinter einem Punkt.** Eine Wortgrenze braucht ein Wortzeichen daneben;
# nach dem Punkt in „S.A." oder „e. K." steht keines, das Muster greift dann nie.
# Deshalb sind gepunktete Rechtsformen von den Wortformen getrennt — beide Listen
# waren zuerst in einer, und „Air Liquide S.A." wie „Meier e. K." fielen durch.
_KONZERN = re.compile(
    r"\b(?:Holding|Group|Gruppe|Konzern|International|Global|Europe|Deutschland|"
    r"SE|AG|KGaA|PLC|Inc|Corp|LLC)\b"
    r"|S\.\s?A\.|S\.p\.A\.|N\.\s?V\.|B\.\s?V\.|Corp\.",
)
_MITTELSTAND = re.compile(
    r"\b(?:GmbH|gGmbH|mbH|KG|OHG|GbR|UG|eG)\b"
    r"|e\.\s?K\.|e\.\s?G\.",
)


def orgtyp(company: str) -> str:
    """Organisationstyp aus dem Namen ableiten. Rein.

    Nur eine Ableitung aus dem Namen, kein Firmenbuch-Abgleich — deshalb heißt der
    Rest ehrlich `unbekannt` statt geraten zu werden. Öffentliche Träger zuerst: Ein
    „Klinikum … GmbH" ist beides, die Trägerschaft ist die wichtigere Information.
    """
    name = (company or "").strip()
    if not name:
        return "unbekannt"
    if _OEFFENTLICH.match(name):
        return "oeffentlich"
    if _KONZERN.search(name):
        return "konzern"
    if _MITTELSTAND.search(name):
        return "mittelstand"
    return "unbekannt"


def score_teile(
    *, systeme: int, hat_baustein: bool, produkt_score: int, hat_website: bool,
) -> dict[str, int]:
    """Die Bestandteile einzeln — damit der Score nachrechenbar bleibt. Rein.

    Bewusst ein Wörterbuch und keine Zahl: Die Oberfläche zeigt die Bestandteile an,
    und wer die Reihenfolge anzweifelt, kann sehen, woraus sie entsteht.
    """
    mehrfach = min(W_MEHRFACH_MAX, max(0, systeme - 1) * W_MEHRFACH_JE_SYSTEM)
    return {
        "mehrfachnutzung": mehrfach,
        "baustein": W_BAUSTEIN if hat_baustein else 0,
        "umfeld": round(max(0, min(100, produkt_score)) * W_PRODUKT_MAX / 100),
        "ansprechbar": W_WEBSITE if hat_website else 0,
    }


def gesamt_score(teile: dict[str, int]) -> int:
    """Summe der Bestandteile, auf 0–100 begrenzt. Rein."""
    return min(100, sum(teile.values()))


def bewerte(
    *, company: str, systeme: int, hat_baustein: bool, produkt_score: int,
    hat_website: bool,
) -> dict:
    """Vollständige Bewertung einer Firma: Score, Bestandteile, Organisationstyp."""
    teile = score_teile(
        systeme=systeme, hat_baustein=hat_baustein,
        produkt_score=produkt_score, hat_website=hat_website,
    )
    return {
        "score": gesamt_score(teile),
        "score_teile": teile,
        "orgtyp": orgtyp(company),
        "systeme": max(1, systeme),
    }


SORTIERUNGEN = ("score", "systeme", "company")


def sortiere(zeilen: list[dict], sort: str) -> list[dict]:
    """Nach Score, Systemzahl oder Name sortieren. Rein.

    In Python, nicht in SQL — dieselbe Begründung wie bei den Katalog-Aggregaten: Der
    Score entsteht aus einem Aggregat über den ganzen Bestand (wie viele Systeme nutzt
    diese Firma?) und ist keine Spalte. Bei 3.712 Zeilen ist das unkritisch; ab etwa
    10.000 gehört die Sortierung in die Datenbank und der Score in eine Spalte.

    Zweitschlüssel ist immer der Name: Ohne ihn wäre die Reihenfolge bei gleichem
    Score von der Datenbank abhängig und würde zwischen zwei Seitenaufrufen wechseln.
    """
    if sort == "systeme":
        return sorted(zeilen, key=lambda z: (-z["systeme"], -z["score"], z["company"].lower()))
    if sort == "company":
        return sorted(zeilen, key=lambda z: z["company"].lower())
    return sorted(zeilen, key=lambda z: (-z["score"], z["company"].lower()))
