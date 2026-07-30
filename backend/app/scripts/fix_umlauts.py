"""Transliterierte Umlaute im Bestand zurückverwandeln (`ae/oe/ue` → `ä/ö/ü`).

    docker compose exec backend python -m app.scripts.fix_umlauts --owner martin
    ... --apply          # schreibt (Standard: Trockenlauf mit vollständigem Vergleich)
    ... --zeige 40       # wie viele Beispiele im Trockenlauf

**Warum es dieses Skript zusätzlich zum Import gibt.** Die Korrektur sitzt in
`market_import._coerce`, damit jeder künftige Katalog korrekt landet. Der Bestand wurde
aber vor dieser Änderung eingespielt — und ein Re-Import wäre der falsche Weg, ihn zu
heilen: Er bräuchte die Katalogdatei und würde den `catalog_stand` fälschlich
fortschreiben. Dieses Skript arbeitet auf denselben reinen Funktionen.

**Was NICHT angefasst wird:** Adressspalten (`ref_url`, `website`, Slugs, `catalog_id`)
und alles außerhalb der Katalogtexte. Firmennamen in `market_references` bleiben
ebenfalls unberührt — die sind aus fremden Seiten geerntet und tragen dort schon
korrekte Umlaute (315 von 3.978); eine Korrektur wäre dort ein Eingriff in Fremddaten.

**Leads werden mitgezogen.** Die Briefings in `rainmaker_leads.notes` sind Kopien des
Produkttexts (s. `market_reference_pipeline.briefing`) — ohne sie wäre die Korrektur auf
halbem Weg stehen geblieben.
"""
import argparse
import asyncio
import sys

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.market_baustein import MarketBaustein
from app.models.market_product import MarketProduct
from app.models.rainmaker_lead import RainmakerLead
from app.models.user import User
from app.services.umlaut import entschluessele, entschluessele_liste
from app.tenancy import current_owner_id

# Textfelder je Modell. Adressspalten und Schlüssel stehen bewusst NICHT drin.
PRODUKT_TEXT = ("produkt", "hersteller", "vendor", "konzern", "kategorie", "kunden",
                "zielgruppe", "nutzen", "integration", "notiz", "ops_note",
                "decision_maker")
PRODUKT_LISTE = ("branchen", "prozesse", "nutzer", "pains", "ki", "mp_evidence", "reg")
BAUSTEIN_TEXT = ("titel", "was", "warum", "vorsicht", "aufwand")
# Nur die Marktradar-Leads: Ihre Notizen sind Kopien des Katalogtexts. Fremde Leads
# (LinkedIn, Discovery, Handarbeit) fasst dieses Skript nicht an.
LEAD_QUELLEN = ("Marktradar", "Marktradar-Referenz")
LEAD_TEXT = ("notes", "target")


async def _owner(db, benutzer: str):
    row = (await db.execute(
        select(User).where((User.username == benutzer) | (User.email == benutzer))
    )).scalar_one_or_none()
    if row is None:
        print(f"Benutzer '{benutzer}' nicht gefunden.", file=sys.stderr)
        raise SystemExit(2)
    return row.id


def _felder(obj, text: tuple, liste: tuple = ()) -> list[tuple[str, object, object]]:
    """Welche Felder würden sich ändern? Rein bis auf das Lesen des Objekts."""
    aus = []
    for f in text:
        alt = getattr(obj, f, None)
        if isinstance(alt, str):
            neu = entschluessele(alt)
            if neu != alt:
                aus.append((f, alt, neu))
    for f in liste:
        alt = getattr(obj, f, None)
        if isinstance(alt, list):
            neu = entschluessele_liste(alt)
            if neu != alt:
                aus.append((f, alt, neu))
    return aus


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--apply", action="store_true", help="schreiben (Standard: Trockenlauf)")
    ap.add_argument("--zeige", type=int, default=25, help="Beispiele im Trockenlauf")
    args = ap.parse_args()

    async with async_session_factory() as db:
        current_owner_id.set(await _owner(db, args.owner))

        zaehler: dict[str, int] = {}
        beispiele: list[str] = []

        async def durch(modell, text, liste=(), label="", filter_=None):
            q = select(modell)
            if filter_ is not None:
                q = q.where(filter_)
            n_obj = n_feld = 0
            for obj in (await db.execute(q)).scalars():
                aenderungen = _felder(obj, text, liste)
                if not aenderungen:
                    continue
                n_obj += 1
                n_feld += len(aenderungen)
                for feld, alt, neu in aenderungen:
                    if len(beispiele) < args.zeige:
                        a = str(alt)[:70]
                        b = str(neu)[:70]
                        beispiele.append(f"  {label}.{feld}\n      {a}\n   →  {b}")
                    if args.apply:
                        setattr(obj, feld, neu)
            zaehler[label] = n_obj
            zaehler[f"{label} (Felder)"] = n_feld

        await durch(MarketProduct, PRODUKT_TEXT, PRODUKT_LISTE, "market_products")
        await durch(MarketBaustein, BAUSTEIN_TEXT, (), "market_bausteine")
        await durch(RainmakerLead, LEAD_TEXT, (), "rainmaker_leads",
                    RainmakerLead.source.in_(LEAD_QUELLEN))

        if args.apply:
            await db.commit()

        print(f"{'Geschrieben' if args.apply else 'TROCKENLAUF'}:\n")
        for k, v in zaehler.items():
            print(f"  {k:28} {v:5}")
        if beispiele:
            print(f"\nBeispiele (max. {args.zeige}):")
            for b in beispiele:
                print(b)
        if not args.apply:
            print("\nNichts geschrieben. Mit --apply wiederholen.")


if __name__ == "__main__":
    asyncio.run(main())
