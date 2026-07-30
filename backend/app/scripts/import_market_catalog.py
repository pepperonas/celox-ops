"""Marktradar-Katalog von der Kommandozeile einspielen.

    docker compose exec backend python -m app.scripts.import_market_catalog \\
        /tmp/ops-catalog.json --owner martin
    ... --dry-run       zeigt nur, was passieren würde

Die Datei erzeugt `dashboard.py` im Recherche-Repo `pepperonas/business-opportunities`
(`data/ops-catalog.json`). Der Import ist idempotent; der eigene Bearbeitungsstand
(Status, Notiz, verknüpfter Lead) bleibt erhalten.

`--owner` ist Pflicht: Katalogeinträge sind besitzergebunden. Ohne gesetzten
Mandanten landen die Zeilen mit `owner_id = NULL` und sind für niemanden
sichtbar — genau das passiert, wenn `app.main` nicht importiert wird, weil dann
die Tenancy-Events gar nicht installiert sind.
"""
import argparse
import asyncio
import json
import pathlib
import sys

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.user import User
from app.services.market_import import import_catalog
from app.tenancy import current_owner_id


async def run(args: argparse.Namespace) -> int:
    path = pathlib.Path(args.datei)
    if not path.exists():
        print(f"FEHLER: Datei nicht gefunden: {path}", file=sys.stderr)
        return 2
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FEHLER: keine gültige JSON-Datei ({exc})", file=sys.stderr)
        return 2

    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.username == args.owner))).scalar_one_or_none()
        if user is None:
            print(f"FEHLER: Benutzer '{args.owner}' nicht gefunden.", file=sys.stderr)
            return 2
        token = current_owner_id.set(user.works_for_id or user.id)
        try:
            result = await import_catalog(db, catalog)
            if args.dry_run:
                await db.rollback()
            else:
                await db.commit()
        except ValueError as exc:
            print(f"FEHLER: {exc}", file=sys.stderr)
            return 2
        finally:
            current_owner_id.reset(token)

    print(f"Katalogstand {result['stand']}{' (Trockenlauf)' if args.dry_run else ''} → {args.owner}")
    print(f"  angelegt      {result['angelegt']}")
    print(f"  aktualisiert  {result['aktualisiert']}")
    print(f"  unveraendert  {result['unveraendert']}")
    print(f"  Bausteine     {result['bausteine']}")
    if result["verwaist"]:
        print(f"  verwaist (nicht mehr im Katalog, bleiben stehen): {', '.join(result['verwaist'])}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Marktradar-Katalog importieren (idempotent).")
    p.add_argument("datei", help="Pfad zur ops-catalog.json")
    p.add_argument("--owner", required=True, help="Benutzername, dem der Katalog gehört")
    p.add_argument("--dry-run", action="store_true", help="nichts schreiben, nur zählen")
    return asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
