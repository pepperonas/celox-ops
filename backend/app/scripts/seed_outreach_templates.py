"""Fehlende Standard-Akquise-Vorlagen in bestehende Arbeitsbereiche nachziehen.

Wofür: Der Seed-Endpunkt wird vom Frontend nur ausgelöst, wenn eine ganze Rubrik
fehlt. Kommt eine zweite Serie INNERHALB einer bestehenden Rubrik hinzu, erreicht
sie einen Arbeitsbereich sonst nie — der Text stünde im Code und nirgends in der
Anwendung.

Ergänzt je Arbeitsbereich genau die Vorlagen, deren (Kanal, Rubrik, Titel) dort
noch nicht existiert. Bestehende bleiben unangetastet: Favoriten, Kopierzähler und
eigene Änderungen überleben.

    python -m app.scripts.seed_outreach_templates            # Trockenlauf
    python -m app.scripts.seed_outreach_templates --apply
"""
import argparse
import asyncio
from collections import defaultdict

from sqlalchemy import select

from app.database import async_session_factory
from app.models import registry  # noqa: F401  — vollständige Metadata, s. Modul-Docstring
from app.models.outreach_template import OutreachTemplate
from app.services.outreach_seed import missing_templates, template_key


def _v(x):
    return x.value if hasattr(x, "value") else x


async def run(apply: bool) -> int:
    async with async_session_factory() as db:
        rows = (await db.execute(select(OutreachTemplate))).scalars().all()
        # Ohne gesetzten ContextVar liest das Skript global — die Vorlagen aller
        # Arbeitsbereiche. Gruppiert wird deshalb selbst nach owner_id.
        by_owner: dict[object, set] = defaultdict(set)
        for t in rows:
            by_owner[t.owner_id].add(template_key(
                {"channel": _v(t.channel), "category": _v(t.category), "title": t.title}
            ))

        total = 0
        for owner_id, existing in sorted(by_owner.items(), key=lambda kv: str(kv[0])):
            fehlend = missing_templates(existing)
            print(f"Bereich {owner_id}: {len(existing)} vorhanden, {len(fehlend)} fehlen")
            for t in fehlend:
                print(f"    + [{t['channel']}/{t['category']}] {t['title']}")
                if apply:
                    db.add(OutreachTemplate(owner_id=owner_id, **t))
            total += len(fehlend)

        if apply and total:
            await db.commit()

    print(f"\n{'Ergänzt' if apply else 'Würde ergänzen'}: {total}")
    if not apply and total:
        print("Nichts geschrieben. Mit --apply ausführen.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    return asyncio.run(run(ap.parse_args().apply))


if __name__ == "__main__":
    raise SystemExit(main())
