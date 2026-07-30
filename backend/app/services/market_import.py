"""Import des Marktradar-Katalogs (`ops-catalog.json`) — idempotent.

Die Datei kommt aus dem privaten Recherche-Repo `pepperonas/business-opportunities`
(dort erzeugt `dashboard.py` sie neben dem statischen Dashboard). Der Import ist
ein **Upsert über `catalog_id`**: derselbe Katalog zweimal eingespielt erzeugt
keine Dubletten.

Die entscheidende Regel steht in `_KATALOG_FELDER` / `_OPS_FELDER`: Nur
Katalogfelder werden überschrieben. Bearbeitungsstand (`status`, `ops_note`, `rainmaker_lead_id`, `reviewed_at`,
`pushed_at`) UND die angereicherten Kontaktdaten (`website`, `email`, `phone`,
`decision_maker`, `employee_count`, …) gehören ops und bleiben unangetastet —
sonst würde eine Katalog-Aktualisierung eigene Arbeit löschen.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_baustein import MarketBaustein
from app.models.market_product import MarketProduct
from app.services.umlaut import entschluessele, entschluessele_liste

# Katalogfeld (JSON) -> Spalte. Alles hier drin wird beim Re-Import überschrieben.
_KATALOG_FELDER: dict[str, str] = {
    "produkt": "produkt",
    "hersteller": "hersteller",
    "vendor": "vendor",
    "vendorSlug": "vendor_slug",
    "konzern": "konzern",
    "konzernSlug": "konzern_slug",
    "kategorie": "kategorie",
    "refUrl": "ref_url",
    "refStatus": "ref_status",
    "urlOk": "url_ok",
    "urlGeprueft": "url_geprueft",
    "refs": "refs",
    "kunden": "kunden",
    "zielgruppe": "zielgruppe",
    "branchen": "branchen",
    "prozesse": "prozesse",
    "nutzer": "nutzer",
    "pains": "pains",
    "ki": "ki",
    "nutzen": "nutzen",
    "integration": "integration",
    "intLevel": "int_level",
    "ease": "ease",
    "notiz": "notiz",
    "lead": "lead",
    "business": "business",
    "prio": "prio",
    "dach": "dach",
    "score": "score",
    "breakdown": "breakdown",
    "marketplace": "marketplace",
    "mpEvidence": "mp_evidence",
    "reg": "reg",
    "selfCompete": "self_compete",
}

# Gehört ops, nicht dem Katalog — hier fasst der Import nichts an.
# Ops-Felder: Bearbeitungsstand UND angereicherte Kontaktdaten. Beides ist Arbeit,
# die nicht im Katalog steht — ein Re-Import darf sie nicht löschen.
_OPS_FELDER = (
    "status", "ops_note", "rainmaker_lead_id", "reviewed_at", "pushed_at",
    "website", "email", "email_status", "phone", "decision_maker",
    "employee_count", "contact_evidence", "contact_checked_at",
)


# Spalten, die Adressen tragen — dort NICHT an den Buchstaben drehen. Der
# Umlaut-Rückbau lässt Adressen ohnehin stehen (`_ADRESSE`), aber hier ist es
# ausdrücklich: In einer URL hat eine Textkorrektur nichts zu suchen.
_ADRESS_SPALTEN = ("ref_url", "website", "vendor_slug", "konzern_slug", "catalog_id")


def _coerce(spalte: str, wert: Any) -> Any:
    if wert is None:
        return None
    if spalte == "ease":
        return Decimal(str(wert))
    if spalte in ("url_ok", "marketplace", "self_compete"):
        return bool(wert)
    if spalte in ("refs", "lead", "business", "score"):
        return int(wert)
    # **Umlaute beim Import zurückverwandeln.** Das Recherche-Repo schreibt
    # `ae/oe/ue`; hier ist die einzige Stelle, an der Katalogtext in die Datenbank
    # kommt. Würde die Korrektur nur nachträglich über den Bestand laufen, hätte der
    # nächste Import sie wieder überschrieben (`_KATALOG_FELDER` gewinnt).
    if spalte in _ADRESS_SPALTEN:
        return wert
    if isinstance(wert, str):
        return entschluessele(wert)
    if isinstance(wert, list):
        return entschluessele_liste(wert)
    return wert


async def import_catalog(db: AsyncSession, catalog: dict) -> dict:
    """Spielt Produkte und Bausteine ein. Gibt eine Zählung zurück.

    Der Aufrufer committet — so kann ein CLI-Skript einen Trockenlauf fahren.
    """
    stand = catalog.get("stand")
    produkte = catalog.get("produkte") or []
    bausteine = catalog.get("bausteine") or []
    if not produkte:
        raise ValueError("Katalog enthält keine Produkte — falsche Datei?")

    vorhanden = {
        p.catalog_id: p
        for p in (await db.execute(select(MarketProduct))).scalars().all()
    }

    angelegt = aktualisiert = unveraendert = 0
    gesehen: set[str] = set()

    for src in produkte:
        cid = src.get("id")
        if not cid:
            continue
        gesehen.add(cid)
        row = vorhanden.get(cid)
        neu = row is None
        if neu:
            row = MarketProduct(catalog_id=cid)
            db.add(row)

        geaendert = False
        for key, spalte in _KATALOG_FELDER.items():
            wert = _coerce(spalte, src.get(key))
            if getattr(row, spalte, None) != wert:
                setattr(row, spalte, wert)
                geaendert = True
        if row.catalog_stand != stand:
            row.catalog_stand = stand
            geaendert = True

        if neu:
            angelegt += 1
        elif geaendert:
            aktualisiert += 1
        else:
            unveraendert += 1

    # Bausteine: vollständig ersetzen. Sie tragen keinen eigenen Bearbeitungsstand,
    # und ein weggefallener Baustein soll nicht als Leiche stehen bleiben.
    for alt in (await db.execute(select(MarketBaustein))).scalars().all():
        await db.delete(alt)
    for b in bausteine:
        db.add(MarketBaustein(
            nr=int(b.get("nr", 0)),
            # Auch hier Umlaute zurückverwandeln: Fünf Bausteine tragen `ae/oe/ue`.
            # `catalog_ids` bleibt unangetastet — das sind Schlüssel, kein Text.
            titel=entschluessele(b.get("titel", "")) or "",
            was=entschluessele(b.get("was")),
            warum=entschluessele(b.get("warum")),
            vorsicht=entschluessele(b.get("vorsicht")),
            aufwand=entschluessele(b.get("aufwand")),
            catalog_ids=b.get("ids") or [],
        ))

    # Verwaist = in ops vorhanden, im neuen Katalog nicht mehr. Bewusst NICHT
    # gelöscht: an so einem Eintrag kann ein Lead hängen. Nur melden.
    verwaist = sorted(set(vorhanden) - gesehen)

    return {
        "stand": stand,
        "angelegt": angelegt,
        "aktualisiert": aktualisiert,
        "unveraendert": unveraendert,
        "bausteine": len(bausteine),
        "verwaist": verwaist,
    }
