"""Einmal-Umstellung: tagesgenaue Hostinger-Herkunftsschlüssel → Periodenschlüssel.

Warum nötig: der erste Entwurf schrieb `hostinger:<abo>:2026-07-04`. Hostinger
richtet Verlängerungstermine aber nachträglich aus — verschiebt sich der Termin um
drei Tage, ergibt `last_billed_on` einen anderen Tag, damit einen anderen Schlüssel
und der nächste Import bucht **denselben Zeitraum ein zweites Mal**. Neu ist der
Schlüssel deshalb periodenbasiert (`…:2026` bzw. `…:2026-07`).

Bestehende Buchungen müssen mitwandern, sonst erkennt der Import sie nicht wieder
und legt sie erneut an.

Die Abrechnungsperiode je Abo steht nur in der API — das Skript liest sie dort und
ordnet über die Abo-ID zu. Ist ein Abo nicht mehr im Konto, bleibt die Zeile
unangetastet und wird gemeldet (ein zerschossener Schlüssel wäre schlimmer als ein
alter).

    python -m app.scripts.migrate_hostinger_refs --user <mail|username>   # Trockenlauf
    python -m app.scripts.migrate_hostinger_refs --user <…> --apply
"""
import argparse
import asyncio
import sys

import httpx
from sqlalchemy import or_, select

from app.database import async_session_factory
from app.models.expense import Expense
from app.models.user import User
from app.services.hostinger import REF_PREFIX, HostingerError, fetch_account, migrated_ref
from app.tenancy import current_owner_id


async def _units_by_subscription(key: str) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        account = await fetch_account(key, client)
    return {s["id"]: (s.get("billing_period_unit") or "month")
            for s in account["subscriptions"] if isinstance(s, dict) and s.get("id")}


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True, help="Kontoinhaber (E-Mail oder Benutzername)")
    parser.add_argument("--apply", action="store_true", help="schreiben (sonst Trockenlauf)")
    args = parser.parse_args()

    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(or_(
            User.username == args.user, User.email == args.user,
            User.google_email == args.user)))).scalars().first()
        if user is None:
            print(f"Kein Nutzer '{args.user}' gefunden.")
            return 2
        if user.works_for_id is not None:
            print("Das ist ein Mitarbeiter-Konto — bitte den Bereichs-Inhaber angeben.")
            return 2

        token = current_owner_id.set(user.id)
        from app.models.app_settings import AppSettings
        settings_row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
        api_key = (settings_row.hostinger_api_key or "").strip() if settings_row else ""
        if not api_key:
            print("Für diesen Arbeitsbereich ist kein Hostinger-Key hinterlegt.")
            return 2

        rows = (await db.execute(select(Expense).where(
            Expense.external_ref.like(f"{REF_PREFIX}:%")))).scalars().all()
        print(f"Bereich '{user.username}': {len(rows)} Buchungen mit Hostinger-Herkunft")

        try:
            units = await _units_by_subscription(api_key)
        except HostingerError as exc:
            print(f"Hostinger-Abruf fehlgeschlagen: {exc}")
            return 1

        changed, skipped, collisions = [], [], []
        seen: dict[str, str] = {}
        for row in rows:
            sub_id = row.external_ref.split(":")[1] if ":" in row.external_ref else ""
            unit = units.get(sub_id)
            if unit is None:
                skipped.append((row.external_ref, "Abo nicht mehr im Konto"))
                continue
            new_ref = migrated_ref(row.external_ref, unit)
            if new_ref is None:
                skipped.append((row.external_ref, "kein tagesgenaues Muster"))
                continue
            if new_ref == row.external_ref:
                continue
            if new_ref in seen:
                # Zwei alte Zeilen fallen auf dieselbe Periode: die zweite wäre ein
                # Duplikat. NICHT stillschweigend zusammenführen — melden.
                collisions.append((row.external_ref, new_ref, seen[new_ref]))
                continue
            seen[new_ref] = row.external_ref
            changed.append((row, new_ref))

        for row, new_ref in changed:
            print(f"  {row.external_ref}  →  {new_ref}    ({row.date}, {row.amount} EUR)")
        for ref, reason in skipped:
            print(f"  übersprungen: {ref} — {reason}")
        for old, new, other in collisions:
            print(f"  KOLLISION: {old} → {new} (belegt von {other}) — "
                  "beide Zeilen prüfen, hier wird nichts geändert")

        print(f"\n{len(changed)} zu ändern · {len(skipped)} übersprungen · "
              f"{len(collisions)} Kollisionen")
        if not args.apply:
            print("Trockenlauf — nichts geschrieben. Mit --apply ausführen.")
            current_owner_id.reset(token)
            return 0

        for row, new_ref in changed:
            row.external_ref = new_ref
        await db.commit()
        print(f"{len(changed)} Herkunftsschlüssel umgestellt.")
        current_owner_id.reset(token)
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
