"""Referenzkunden der Katalog-Hersteller ernten — die eigentlichen Lead-Kandidaten.

    docker compose exec backend python -m app.scripts.harvest_market_references \\
        --owner martin                    # Trockenlauf über die öffentlichen Verzeichnisse
    ... --apply                           # schreibt in market_references
    ... --limit 20 --min-marker 0.3       # erst wenige, nur saubere Ernten
    ... --only-missing                    # Hersteller ohne bisherige Ernte
    ... --all-status                      # auch „teilweise"/„unklar"-Verzeichnisse

Zum Lead wird nicht der Hersteller, sondern wer seine Software EINSETZT: „Sie arbeiten
mit [Software X] — ich baue [Baustein N] darauf." Das Muster von bcsbook.

**Gemessen, nicht geschätzt** (Lauf über die 20 größten Verzeichnisse): 14 von 20
liefern Firmen, 2.595 Namen. Sechs liefern nichts — umgeleitete URL, JS-gerenderte
Liste, oder gar keine Liste im HTML. Das ist der ehrliche Erwartungswert; die 8.664
werden es über statisches HTML nicht.

Der Lauf ist **idempotent**: Eindeutig ist eine Firma pro Hersteller (dieselbe Firma
bei zwei Herstellern nutzt zwei Systeme — kein Duplikat, sondern der bessere Lead).
Ein zweiter Lauf ergänzt neue Namen und lässt den Bearbeitungsstand in Ruhe.
"""
import argparse
import asyncio
import sys

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.database import async_session_factory
from app.models.market_product import MarketProduct
from app.models.market_reference import MarketReference, norm_company
from app.models.user import User
from app.services.market_references import ernte_fuer_verzeichnis, marker_anteil
from app.tenancy import current_owner_id


async def _owner_id(db, benutzer: str):
    row = (await db.execute(
        select(User).where((User.username == benutzer) | (User.email == benutzer))
    )).scalar_one_or_none()
    if row is None:
        print(f"Benutzer '{benutzer}' nicht gefunden.", file=sys.stderr)
        raise SystemExit(2)
    return row.id


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--apply", action="store_true", help="schreiben (Standard: Trockenlauf)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only-missing", action="store_true",
                    help="nur Hersteller ohne bisher geerntete Referenzen")
    ap.add_argument("--all-status", action="store_true",
                    help="auch Verzeichnisse mit ref_status teilweise/unklar")
    ap.add_argument("--min-marker", type=float, default=0.0,
                    help="Ernte nur übernehmen, wenn dieser Anteil der Namen eine "
                         "Rechtsform trägt (Qualitätsschwelle, 0 = alles)")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    async with async_session_factory() as db:
        current_owner_id.set(await _owner_id(db, args.owner))

        q = select(MarketProduct).order_by(MarketProduct.refs.desc())
        if not args.all_status:
            q = q.where(MarketProduct.ref_status == "oeffentlich")
        if args.only_missing:
            schon = select(MarketReference.product_id).distinct().subquery()
            q = q.where(MarketProduct.id.not_in(select(schon.c.product_id)))
        if args.limit:
            q = q.limit(args.limit)
        produkte = list((await db.execute(q)).scalars())
        print(f"{len(produkte)} Verzeichnisse{' — TROCKENLAUF' if not args.apply else ''}\n")

        sem = asyncio.Semaphore(max(1, args.concurrency))

        async def einer(p: MarketProduct):
            async with sem:
                return p, await ernte_fuer_verzeichnis(p.ref_url, p.refs, p.vendor)

        gesamt = neu = uebersprungen = 0
        mit_ernte = 0
        for coro in asyncio.as_completed([einer(p) for p in produkte]):
            p, e = await coro
            if e.error or not e.namen:
                print(f"  ✗ {p.vendor[:34]:36} {e.error or e.verdikt}")
                continue
            anteil = marker_anteil(e.namen)
            if anteil < args.min_marker:
                uebersprungen += 1
                print(f"  ~ {p.vendor[:34]:36} {len(e.namen):5} Namen — unter der "
                      f"Qualitätsschwelle ({anteil:.0%} < {args.min_marker:.0%})")
                continue
            mit_ernte += 1
            gesamt += len(e.namen)
            print(f"  · {p.vendor[:34]:36} {len(e.namen):5} Namen  {anteil:.0%} Rechtsform"
                  f"  [{e.form}]")

            if not args.apply:
                continue
            for name in e.namen:
                schluessel = norm_company(name)
                if not schluessel:
                    continue
                # Idempotent: pro Hersteller einmal. Ein zweiter Lauf ergänzt nur.
                vorhanden = (await db.execute(
                    select(MarketReference).where(
                        MarketReference.product_id == p.id,
                        MarketReference.company_norm == schluessel,
                    ).limit(1))).scalar_one_or_none()
                if vorhanden is not None:
                    # Website nachtragen, falls sie beim ersten Lauf fehlte.
                    if not vorhanden.website and e.websites.get(name):
                        vorhanden.website = e.websites[name]
                    continue
                db.add(MarketReference(
                    product_id=p.id,
                    company=name[:255],
                    company_norm=schluessel[:255],
                    website=(e.websites.get(name) or None),
                    source_url=p.ref_url,
                    form=e.form,
                ))
                try:
                    async with db.begin_nested():
                        await db.flush()
                    neu += 1
                except IntegrityError:
                    pass                      # Rennen gegen den Unique-Index: egal

        if args.apply:
            await db.commit()
            bestand = (await db.execute(select(func.count(MarketReference.id)))).scalar()
            print(f"\n{mit_ernte} Verzeichnisse geerntet · {gesamt} Namen gefunden · "
                  f"{neu} neu angelegt · Bestand jetzt {bestand}")
        else:
            print(f"\n{mit_ernte} Verzeichnisse würden {gesamt} Namen liefern.")
        if uebersprungen:
            print(f"{uebersprungen} unter der Qualitätsschwelle übersprungen.")
        if not args.apply:
            print("Nichts geschrieben. Mit --apply wiederholen.")


if __name__ == "__main__":
    asyncio.run(main())
