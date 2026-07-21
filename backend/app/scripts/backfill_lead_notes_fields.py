"""Backfill: „Mitarbeiter:"/„Geschäftsführung:" aus Lead-Notizen in die eigenen
Spalten `employee_count` / `decision_maker` ziehen.

Nötig für Leads, die VOR der Einführung dieser Felder per CSV importiert wurden
(die Werte stecken dort noch im Notiz-Block). Die betroffenen Notiz-Zeilen werden
danach entfernt, damit die Information nicht doppelt steht.

Nur exakt diese zwei Zeilenmuster werden angefasst; alles andere in den Notizen
bleibt unberührt. Ohne `--apply` läuft ein reiner Report.

    docker compose exec backend python -m app.scripts.backfill_lead_notes_fields
    docker compose exec backend python -m app.scripts.backfill_lead_notes_fields --apply
"""
import argparse
import asyncio
import re

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.rainmaker_lead import RainmakerLead
from app.services.lead_csv_import import parse_employee_count

_EMPLOYEE_LINE = re.compile(r"^Mitarbeiter:\s*(.+)$", re.M)
_DECIDER_LINE = re.compile(r"^(?:Geschäftsführung|Vorstand):\s*(.+)$", re.M)


def extract_from_notes(notes: str | None) -> tuple[int | None, str | None, str | None]:
    """(employee_count, decision_maker, bereinigte_notizen) — reine Funktion.
    Gibt (None, None, notes) zurück, wenn nichts zu holen ist."""
    if not notes:
        return None, None, notes

    emp_match = _EMPLOYEE_LINE.search(notes)
    dec_match = _DECIDER_LINE.search(notes)
    if not emp_match and not dec_match:
        return None, None, notes

    employees = parse_employee_count(emp_match.group(1)) if emp_match else None
    decider = dec_match.group(1).strip() if dec_match else None

    cleaned = notes
    # Zeile nur entfernen, wenn ihr Wert auch wirklich übernommen wurde.
    if emp_match and employees is not None:
        cleaned = _EMPLOYEE_LINE.sub("", cleaned, count=1)
    if dec_match and decider:
        cleaned = _DECIDER_LINE.sub("", cleaned, count=1)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip() or None
    return employees, decider, cleaned


async def run(apply: bool) -> int:
    async with async_session_factory() as db:
        # ContextVar ungesetzt ⇒ global über alle Owner (Wartungsskript).
        leads = (await db.execute(select(RainmakerLead))).scalars().all()
        touched = emp_set = dec_set = 0
        samples: list[str] = []

        for lead in leads:
            employees, decider, cleaned = extract_from_notes(lead.notes)
            if employees is None and decider is None:
                continue
            changed = False
            # Vorhandene Werte nie überschreiben (manuelle Pflege gewinnt).
            if employees is not None and lead.employee_count is None:
                lead.employee_count = employees
                emp_set += 1
                changed = True
            if decider and not lead.decision_maker:
                lead.decision_maker = decider
                dec_set += 1
                changed = True
            if changed:
                lead.notes = cleaned
                touched += 1
                if len(samples) < 8:
                    samples.append(f"{lead.company} (MA={employees}, GF={decider})")

        if apply:
            await db.commit()

    mode = "AKTUALISIERT" if apply else "WÜRDE AKTUALISIEREN (dry-run)"
    print(f"{mode}: {touched} Leads · employee_count: {emp_set} · decision_maker: {dec_set}")
    if samples:
        print("Beispiele:")
        for s in samples:
            print(f"  {s}")
    if not apply:
        print("\nNichts geschrieben. Mit --apply erneut ausführen.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Mitarbeiterzahl/Geschäftsführung aus Notizen in Felder ziehen.")
    p.add_argument("--apply", action="store_true", help="Tatsächlich schreiben (ohne = dry-run)")
    args = p.parse_args()
    raise SystemExit(asyncio.run(run(args.apply)))


if __name__ == "__main__":
    main()
