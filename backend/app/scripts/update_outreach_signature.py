"""Einmal-Umstellung: alte Kurz-Signatur in bestehenden Akquise-Vorlagen ersetzen.

Warum nötig: Der Seed schreibt die Signatur in die `body`-Spalte. Eine Änderung
an der Konstante wirkt deshalb NUR auf noch nicht angelegte Vorlagen — bereits
gespeicherte behalten die alte. Ohne dieses Skript trügen die 72 Bestands-
Vorlagen „Beste Grüße / celox.io · Berlin" und die 27 neuen die vollständige
Signatur: zwei Absender in einem Modul.

Ersetzt wird ausschließlich der **exakte** alte Signatur-Block. Kein Muster-Match
auf „alles ab dem ersten Grußwort" — das würde eigene Nachsätze mitlöschen. Ein
Body, der die alte Signatur nicht wörtlich enthält (weil von Hand bearbeitet),
bleibt unangetastet und wird gemeldet.

Läuft absichtlich über ALLE Arbeitsbereiche: Skripte haben keinen ContextVar,
und der Suchtext ist eine konkrete Signatur dieses Absenders — er kann in einem
fremden Text nicht versehentlich zutreffen.

    python -m app.scripts.update_outreach_signature            # Trockenlauf
    python -m app.scripts.update_outreach_signature --apply
"""
import argparse
import asyncio

from sqlalchemy import select

from app.database import async_session_factory
from app.models.outreach_template import OutreachChannel, OutreachTemplate
from app.services.email_signature import LEGACY_TEMPLATE_SIGNATURE, SIGNATURE


async def run(apply: bool) -> int:
    changed: list[str] = []
    already: list[str] = []
    untouched: list[str] = []

    async with async_session_factory() as db:
        rows = (await db.execute(
            select(OutreachTemplate).where(OutreachTemplate.channel == OutreachChannel.email)
        )).scalars().all()

        for t in rows:
            if SIGNATURE in t.body:
                already.append(t.title)
            elif LEGACY_TEMPLATE_SIGNATURE in t.body:
                changed.append(t.title)
                if apply:
                    t.body = t.body.replace(LEGACY_TEMPLATE_SIGNATURE, SIGNATURE)
            else:
                untouched.append(t.title)

        if apply and changed:
            await db.commit()

    print(f"E-Mail-Vorlagen geprüft: {len(rows)}")
    print(f"  aktualisiert{'' if apply else ' (Trockenlauf)'}: {len(changed)}")
    print(f"  hatten die neue Signatur schon: {len(already)}")
    if untouched:
        # Bewusst einzeln aufgelistet: Das sind von Hand bearbeitete Vorlagen.
        # Sie stillschweigend zu überspringen wäre die schlechtere Auskunft — der
        # Nutzer soll wissen, wo er selbst nachziehen muss.
        print(f"  ohne erkennbare alte Signatur (bitte selbst prüfen): {len(untouched)}")
        for title in untouched:
            print(f"    · {title}")
    if not apply and changed:
        print("\nNichts geschrieben. Mit --apply ausführen.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    args = ap.parse_args()
    return asyncio.run(run(args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
