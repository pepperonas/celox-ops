"""Bestandsdaten auf kanonische Taxonomie-Schreibweisen vereinheitlichen.

Dry-Run ist der DEFAULT (druckt geplante Änderungen, schreibt nichts);
erst mit --apply wird geschrieben. Läuft global über alle Owner (ContextVar
unset → unscoped), ändert aber nur Werte, nie Zuordnungen.

    docker compose exec backend python -m app.scripts.normalize_taxonomy_values
    docker compose exec backend python -m app.scripts.normalize_taxonomy_values --apply

Scope: rainmaker_leads.role / .source / .tags (Synonyme + Case-Dubletten,
Tag-Listen werden fold-dedupliziert bei erhaltener Reihenfolge).
"""
import asyncio
import sys

import app.main  # noqa: F401  — registriert alle Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.rainmaker_lead import RainmakerLead
from app.services.taxonomy import canonicalize, fold


def plan_lead_changes(leads: list) -> list[tuple[object, dict]]:
    """Rein & testbar: berechnet je Lead die Feld-Änderungen (alt → neu)."""
    changes = []
    for lead in leads:
        patch: dict = {}
        for attr, field in (("role", "role"), ("source", "source")):
            old = getattr(lead, attr)
            if old:
                new = canonicalize(field, old)
                if new != old:
                    patch[attr] = (old, new)
        if lead.tags:
            new_tags: list[str] = []
            seen: set[str] = set()
            for t in lead.tags:
                canon = canonicalize("tag", t)
                if fold(canon) not in seen:
                    seen.add(fold(canon))
                    new_tags.append(canon)
            if new_tags != list(lead.tags):
                patch["tags"] = (list(lead.tags), new_tags)
        if patch:
            changes.append((lead, patch))
    return changes


async def main(apply: bool) -> None:
    async with async_session_factory() as db:
        leads = (await db.execute(select(RainmakerLead))).scalars().all()
        changes = plan_lead_changes(leads)

        if not changes:
            print("Keine Änderungen nötig — Bestand ist bereits kanonisch.")
            return

        print(f"{'ANWENDEN' if apply else 'DRY-RUN'} — {len(changes)} Lead(s) betroffen:\n")
        for lead, patch in changes:
            for attr, (old, new) in patch.items():
                print(f"  {lead.company[:40]:40} {attr}: {old!r} → {new!r}")

        if apply:
            for lead, patch in changes:
                for attr, (_old, new) in patch.items():
                    setattr(lead, attr, new)
            await db.commit()
            print(f"\n✓ {len(changes)} Lead(s) aktualisiert.")
        else:
            print("\nNichts geschrieben. Mit --apply ausführen, um zu übernehmen.")


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))
