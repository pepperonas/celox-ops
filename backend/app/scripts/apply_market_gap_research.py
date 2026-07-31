"""Forum-/Community-Lückenanalyse in market_products schreiben.

    docker compose exec backend \\
      python -m app.scripts.apply_market_gap_research --owner <user> [--apply]

Datenquelle: `app.data.market_gap_research.GAP_RESEARCH` (142 Produkte).
Trockenlauf als Default. Re-Import des Katalogs überschreibt diese Felder nicht
(`_OPS_FELDER`).
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import app.main  # noqa: F401
from sqlalchemy import select

from app.data.market_gap_research import GAP_RESEARCH, entry_for
from app.database import async_session_factory
from app.models.market_product import MarketProduct
from app.models.user import User
from app.services.business_time import now as business_now
from app.tenancy import current_owner_id


async def _owner_id(db, benutzer: str):
    row = (await db.execute(
        select(User).where((User.username == benutzer) | (User.email == benutzer))
    )).scalar_one_or_none()
    if row is None:
        print(f"Benutzer '{benutzer}' nicht gefunden.", file=sys.stderr)
        raise SystemExit(2)
    return row.id


def _same_list(a, b) -> bool:
    return list(a or []) == list(b or [])


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    async with async_session_factory() as db:
        oid = await _owner_id(db, args.owner)
        token = current_owner_id.set(oid)
        try:
            products = (await db.execute(select(MarketProduct))).scalars().all()
            updated = skipped = missing_data = 0
            stamp = business_now()
            for p in products:
                data = entry_for(p.catalog_id)
                if not data:
                    missing_data += 1
                    print(f"  ? kein Recherche-Eintrag: {p.catalog_id} ({p.produkt})")
                    continue
                forum = list(data["forum_pains"])
                gaps = list(data["vendor_gaps"])
                rem = list(data["remedies"])
                if (
                    _same_list(p.forum_pains, forum)
                    and _same_list(p.vendor_gaps, gaps)
                    and _same_list(p.remedies, rem)
                ):
                    skipped += 1
                    continue
                updated += 1
                print(f"  {'→' if args.apply else '~'} {p.catalog_id}: "
                      f"{len(forum)} Foren · {len(gaps)} Lücken · {len(rem)} Lösungen")
                if args.apply:
                    p.forum_pains = forum
                    p.vendor_gaps = gaps
                    p.remedies = rem
                    p.gap_researched_at = stamp
            print(
                f"{'Geschrieben' if args.apply else 'Trockenlauf'}: "
                f"{updated} ändern, {skipped} unverändert, "
                f"{missing_data} ohne Daten, Katalog {len(GAP_RESEARCH)}."
            )
            if args.apply:
                await db.commit()
        finally:
            current_owner_id.reset(token)


if __name__ == "__main__":
    asyncio.run(main())
