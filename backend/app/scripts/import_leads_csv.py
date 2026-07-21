"""CSV → Pipeline-Import mit „Target" (CLI, für Claude Code / manuell).

Bildet eine Firmen-CSV auf die stabilen Lead-Felder ab (reine Logik in
`services/lead_csv_import.py`), weist allen Zeilen ein `--target` zu und legt sie
über die BESTEHENDE Dedup-/E-Mail-Prüf-Pipeline an — keine Duplikate, `email_status`
gesetzt. Owner-scoped: Leads sind besitzergebunden, daher ist `--owner` Pflicht.

Beispiel (im Backend-Container):
    docker compose exec backend python -m app.scripts.import_leads_csv \
        /pfad/companies.csv --target "Projektron BCS / Zeiterfassung" \
        --owner admin --source "Projektron-Referenzen"

    # lokal (dev):
    docker compose -f docker-compose.dev.yml run --rm \
        -v /Users/martin/claude/_scraped:/data backend \
        python -m app.scripts.import_leads_csv /data/…/companies.csv \
        --target "bcs / zeiterfassung" --owner admin --dry-run

Standardmäßig `--dry-run`-freundlich: ohne `--apply` wird nur berichtet, nichts
geschrieben.
"""
import argparse
import asyncio
import csv
import sys

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.rainmaker_lead import RainmakerLead
from app.models.user import User
from app.services.lead_csv_import import resolve_columns, row_to_lead_fields
from app.tenancy import current_owner_id


def _read_rows(path: str, encoding: str | None, delimiter: str | None):
    """CSV robust lesen: BOM-fähig (utf-8-sig), Delimiter автоerkennen (;/,/\\t)."""
    enc = encoding or "utf-8-sig"
    with open(path, encoding=enc, newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        if delimiter:
            dialect_delim = delimiter
        else:
            try:
                dialect_delim = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
            except csv.Error:
                dialect_delim = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=dialect_delim)
        headers = reader.fieldnames or []
        return headers, list(reader), dialect_delim


async def run(args: argparse.Namespace) -> int:
    from app.routers.rainmaker import (  # lazy: DB-Helfer, vermeidet Import-Zyklen
        _build_dedup_index,
        _email_status_for,
        _safe_flush_lead,
    )
    from app.services.lead_dedup import norm_company  # noqa: F401 (Doku-Parität)

    headers, rows, delim = _read_rows(args.csv, args.encoding, args.delimiter)
    if not headers:
        print("FEHLER: keine Kopfzeile in der CSV gefunden.", file=sys.stderr)
        return 2

    colmap = resolve_columns(headers)
    print(f"Delimiter: {delim!r} · {len(rows)} Zeilen · Spalten-Mapping:")
    for field, header in colmap.items():
        print(f"  {field:13} ← {header!r}")
    if "company" not in colmap:
        print("FEHLER: keine Firmen-Spalte erkennbar — Abbruch.", file=sys.stderr)
        return 2

    async with async_session_factory() as db:
        # Owner auflösen und ContextVar setzen — sonst würden Inserts owner_id=NULL
        # schreiben (global sichtbar) statt dem Zielnutzer zu gehören.
        user = (await db.execute(select(User).where(User.username == args.owner))).scalar_one_or_none()
        if not user:
            print(f"FEHLER: Benutzer '{args.owner}' nicht gefunden.", file=sys.stderr)
            return 2
        token = current_owner_id.set(user.id)
        try:
            idx, _ = await _build_dedup_index(db)
            mx_cache: dict = {}
            created = 0
            skipped_dupe = 0
            skipped_empty = 0
            samples: list[str] = []

            for row in rows:
                fields = row_to_lead_fields(row, colmap, target=args.target, source=args.source)
                if not fields:
                    skipped_empty += 1
                    continue
                # Dedup gegen Bestand UND batch-intern (E-Mail → Website → Name).
                match, _reason = idx.match(
                    email=fields["email"], website=fields["website"],
                    name=fields["contact_name"],
                )
                if match:
                    skipped_dupe += 1
                    continue

                fields["email_status"] = await _email_status_for(fields["email"], mx_cache)
                lead = RainmakerLead(**fields)
                if args.apply:
                    if not await _safe_flush_lead(db, lead):
                        skipped_dupe += 1  # Race gegen Unique-Index
                        continue
                idx.add(lead, email=fields["email"], website=fields["website"], name=fields["contact_name"])
                created += 1
                if len(samples) < 8:
                    samples.append(fields["company"])

            if args.apply:
                await db.commit()
        finally:
            current_owner_id.reset(token)

    mode = "ANGELEGT" if args.apply else "WÜRDE ANLEGEN (dry-run)"
    print(f"\n{mode}: {created}")
    print(f"Übersprungen — Duplikat: {skipped_dupe} · ohne Firma: {skipped_empty}")
    if samples:
        print("Beispiele:", " · ".join(samples))
    if not args.apply:
        print("\nNichts geschrieben. Mit --apply erneut ausführen, um zu importieren.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Firmen-CSV als Leads mit Target importieren.")
    p.add_argument("csv", help="Pfad zur CSV-Datei")
    p.add_argument("--target", required=True, help="Target/Pain für alle Zeilen, z. B. 'bcs / zeiterfassung'")
    p.add_argument("--owner", required=True, help="Benutzername, dem die Leads gehören (owner_id)")
    p.add_argument("--source", default="CSV-Import", help="Quelle-Label (Default: CSV-Import)")
    p.add_argument("--delimiter", default=None, help="CSV-Trennzeichen (Default: automatisch)")
    p.add_argument("--encoding", default=None, help="Datei-Encoding (Default: utf-8-sig)")
    p.add_argument("--apply", action="store_true", help="Tatsächlich schreiben (ohne = dry-run)")
    args = p.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
