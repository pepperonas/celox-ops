"""Einmal-Umstellung: die bcsbook-Vorlagen auf die allgemeine Erzählung bringen.

Warum nötig: Der Seed schreibt Texte in die `body`-Spalte. Eine Änderung am Seed
wirkt deshalb NUR auf noch nicht angelegte Vorlagen — die 15 bcsbook-Vorlagen
liegen längst in der Datenbank und behielten sonst für immer die alte,
entwicklerlastige Fassung („Commits, IDE-Aktivität, Ticket-Updates").

**Ersetzt wird nur, was noch unverändert ist.** Verglichen wird die Prüfsumme des
gespeicherten Textes mit der des ALTEN Seeds (unten festgehalten). Passt sie, ist
der Text nachweislich nicht von Hand bearbeitet und darf ersetzt werden. Passt sie
nicht, bleibt die Vorlage unangetastet und wird gemeldet — eigene Formulierungen zu
überschreiben wäre schlimmer als eine alte Fassung stehen zu lassen.

Prüfsummen statt der alten Volltexte: dieselbe Sicherheit, ein Fünfzigstel des
Umfangs.

    python -m app.scripts.update_bcsbook_templates            # Trockenlauf
    python -m app.scripts.update_bcsbook_templates --apply
"""
import argparse
import asyncio
import hashlib

from sqlalchemy import select

from app.database import async_session_factory
from app.models import registry  # noqa: F401  — vollständige Metadata, s. Modul-Docstring
from app.models.outreach_template import OutreachTemplate
from app.services.outreach_seed import default_templates

# Prüfsumme des Textes VOR der Überarbeitung, je „kanal|titel".
ALTE_PRUEFSUMMEN: dict[str, str] = {
    'email|3.300 € pro Person und Jahr (kaufmännische Leitung)': "127d0de645fa7ec742eab78191c6d4f9e574448ff1bca28bb17f98f16baf3914",
    'email|Aus eigener Praxis entstanden': "5f14deb420851b9000a7d66118eda7deafce32d56fc13bbbc866dea48f15720a",
    'email|Beweis vor Kauf: der Pilot': "64397014dfb00a2f3dd32b6cbaa414437a530c1bbae6103253f721850f243150",
    'email|Freitags acht Stunden erinnern (Teamleitung)': "dc240599e029efd3600a503e0877bdbb2ae54cfc80d89af4a3b89c89b1765d4a",
    'email|Sauberes Controlling (Bestandskunde)': "f02ddd987769316cb260776eca8ea0565a9c40503d3200b22721624ab067a06a",
    'email|Werkzeug statt Aufpasser (Team)': "55183f8b05ecf00019ba48ba605cfcb9377fd242a3e4b41b1e2c1dc54a53a46f",
    'linkedin|3.300 € je Person (kaufm. Leitung)': "af0c112329ce9f2701aa6d84adc639d97a17b9a8b2b55caa79a12e4d31acaef5",
    'linkedin|Aus eigener Praxis': "86e1663dc335204bc68b3a5e8f401dd8b91ba8b22b296e0148e390ba60bb2b5e",
    'linkedin|Beweis vor Kauf': "9f30d5247702d0004821f06741bf578740db70466c5226c58604e0e4dca7b0e0",
    'linkedin|Freitags erinnern (Teamleitung)': "69735a6c8c401bb02815b0cc2bfc9b0e236e7cf9fdc8571688077594c8346ade",
    'linkedin|Kein Aufpasser': "77825b7b49f33b7050a6b029b1dc4283f6caa3243121ae4574f5ab34589428e0",
    'linkedin|Projektkosten stimmen? (Bestandskunde)': "13eb6cba086c8dc5eaf25888122beff61d7e2f499a83646b0509f814311c9c11",
    'phone|Leitfaden Datenqualität (Bestandskunde)': "cbd3e814114b48469b435afe9da4cee0b82f7fc7b6012c160805e58c855e1cf2",
    'phone|Leitfaden ROI (kaufmännische Leitung)': "6d20b05c4f0f1e1cac8e7734df6aefc53b078691fc66c22d7bdcbcc4cfccbda2",
    'phone|Leitfaden Teamleitung / Projektleitung': "6b68563547022c9294f89f5e466272b8d020a4a0057e8e0453ce0598faf0c862",
}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _v(x):
    return x.value if hasattr(x, "value") else x


async def run(apply: bool) -> int:
    neu = {
        f'{t["channel"]}|{t["title"]}': t
        for t in default_templates() if t["category"] == "bcsbook_zeit"
    }

    ersetzt, aktuell, handarbeit, unbekannt = [], [], [], []

    async with async_session_factory() as db:
        rows = (await db.execute(
            select(OutreachTemplate).where(OutreachTemplate.category == "bcsbook_zeit")
        )).scalars().all()

        for row in rows:
            key = f"{_v(row.channel)}|{row.title}"
            ziel = neu.get(key)
            if ziel is None:
                unbekannt.append(key)
                continue
            ist = _hash(row.body)
            if ist == _hash(ziel["body"]):
                aktuell.append(key)
            elif ist == ALTE_PRUEFSUMMEN.get(key):
                ersetzt.append(key)
                if apply:
                    row.body = ziel["body"]
                    row.subject = ziel["subject"]
                    row.notes = ziel["notes"]
            else:
                handarbeit.append(key)

        if apply and ersetzt:
            await db.commit()

    print(f"bcsbook-Vorlagen geprüft: {len(rows)}")
    print(f"  {'ersetzt' if apply else 'zu ersetzen'}: {len(ersetzt)}")
    for k in ersetzt:
        print(f"    ~ {k}")
    print(f"  schon auf dem neuen Stand: {len(aktuell)}")
    if handarbeit:
        # Einzeln aufführen: Das sind von Hand bearbeitete Texte. Sie
        # stillschweigend zu überspringen wäre die schlechtere Auskunft.
        print(f"  von Hand geändert, NICHT angetastet: {len(handarbeit)}")
        for k in handarbeit:
            print(f"    ! {k}")
    if unbekannt:
        print(f"  nicht im Standard-Satz: {len(unbekannt)}")
        for k in unbekannt:
            print(f"    ? {k}")
    if not apply and ersetzt:
        print("\nNichts geschrieben. Mit --apply ausführen.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    return asyncio.run(run(ap.parse_args().apply))


if __name__ == "__main__":
    raise SystemExit(main())
