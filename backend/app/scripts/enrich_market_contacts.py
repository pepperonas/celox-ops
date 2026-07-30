"""Marktradar-Einträge mit Kontaktdaten von der Herstellerseite anreichern.

    docker compose exec backend python -m app.scripts.enrich_market_contacts \\
        --owner martin                      # Trockenlauf: zeigt nur, was gefunden wird
    ... --apply                             # schreibt
    ... --only-missing                      # nur Einträge ohne Kontaktprüfung
    ... --limit 10                          # erst an wenigen ausprobieren

Holt je Hersteller die Startseite und (nur falls nötig) die Impressum-/Kontaktseite,
liest **deterministisch** Website, E-Mail, Telefon, Geschäftsführung und — streng
gefiltert — die Mitarbeiterzahl aus und prüft die E-Mail per MX (kostenlos, ohne
SMTP-Verbindung). Jeder Wert ist eine wörtliche Teilzeichenfolge der Seite; zu jedem
Fund wird Quell-URL und Zitat gespeichert (`contact_evidence`).

**Ein leeres Feld ist ein gültiges Ergebnis.** Wo nichts sicher gefunden wird, bleibt
nichts stehen — und ein Lauf, der nichts findet, überschreibt einen früheren Fund
NICHT mit Leere.

`--owner` ist Pflicht: Katalogeinträge sind besitzergebunden, und ein Skript hat
keinen ContextVar. Ohne gesetzten Mandanten sähe der Lauf keine Zeilen.
"""
import argparse
import asyncio
import sys

import app.main  # noqa: F401 — registriert Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.market_product import MarketProduct
from app.models.user import User
from app.services.business_time import now
from app.services.email_verifier import verify_email
from app.services.market_contacts import fetch_contacts
from app.tenancy import current_owner_id

FELDER = ("website", "email", "phone", "decision_maker", "employee_count")


async def _owner_id(db, benutzer: str) -> str:
    row = (await db.execute(
        select(User).where((User.username == benutzer) | (User.email == benutzer))
    )).scalar_one_or_none()
    if row is None:
        print(f"Benutzer '{benutzer}' nicht gefunden.", file=sys.stderr)
        raise SystemExit(2)
    return row.id


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True, help="Benutzername oder E-Mail des Arbeitsbereichs")
    ap.add_argument("--apply", action="store_true", help="schreiben (Standard: Trockenlauf)")
    ap.add_argument("--only-missing", action="store_true",
                    help="nur Einträge ohne contact_checked_at")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=5,
                    help="parallele Abrufe (höflich bleiben)")
    args = ap.parse_args()

    async with async_session_factory() as db:
        owner = await _owner_id(db, args.owner)
        current_owner_id.set(owner)

        q = select(MarketProduct).order_by(MarketProduct.score.desc())
        if args.only_missing:
            q = q.where(MarketProduct.contact_checked_at.is_(None))
        if args.limit:
            q = q.limit(args.limit)
        produkte = list((await db.execute(q)).scalars())
        print(f"{len(produkte)} Einträge{' (nur ungeprüfte)' if args.only_missing else ''}"
              f"{' — TROCKENLAUF' if not args.apply else ''}\n")

        sem = asyncio.Semaphore(max(1, args.concurrency))
        mx_cache: dict = {}

        async def einer(p: MarketProduct):
            async with sem:
                return p, await fetch_contacts(p.ref_url)

        treffer = {f: 0 for f in FELDER}
        fehler = 0
        for coro in asyncio.as_completed([einer(p) for p in produkte]):
            p, f = await coro
            if f.error:
                fehler += 1
                print(f"  ✗ {p.vendor}: {f.error}")
                continue

            # E-Mail deterministisch nachprüfen (MX, kein SMTP) — eine Adresse ohne
            # MX-Eintrag ist kein Kontaktweg, nur eine Zeichenkette.
            status = None
            if f.email:
                pruefung = await verify_email(f.email, mx_cache=mx_cache)
                status = pruefung.status.value if pruefung.status else None
                # **Kaputte Adressen werden verworfen, nicht gespeichert.** Im
                # Trockenlauf kam eine mit `invalid_syntax` zurück — ein Fragment aus
                # minifiziertem Seitencode. Ohne MX ist eine Adresse ebenso kein
                # Kontaktweg, sondern nur eine Zeichenkette. `role` (info@, kontakt@)
                # bleibt: Das IST die Firmenadresse.
                if status in ("invalid_syntax", "no_mx", "disposable"):
                    print(f"    (E-Mail verworfen: {f.email} → {status})")
                    f.email = None
                    f.evidence.pop("email", None)
                    status = None

            gefunden = [x for x in FELDER if getattr(f, x)]
            for x in gefunden:
                treffer[x] += 1
            print(f"  · {p.vendor}: {', '.join(gefunden) or 'nichts'}"
                  + (f"  [{status}]" if status else ""))

            if args.apply:
                # Nie einen vorhandenen Wert mit Leere überschreiben.
                for x in FELDER:
                    neu = getattr(f, x)
                    if neu:
                        setattr(p, x, neu)
                if f.email:
                    p.email_status = status
                if f.evidence:
                    p.contact_evidence = {**(p.contact_evidence or {}), **f.evidence}
                p.contact_checked_at = now()

        if args.apply:
            await db.commit()

        n = len(produkte)
        print(f"\n{'Geschrieben' if args.apply else 'Trockenlauf'}: {n} geprüft, "
              f"{fehler} nicht erreichbar")
        for x in FELDER:
            anteil = f"{treffer[x] / n * 100:.0f}%" if n else "—"
            print(f"  {x:16} {treffer[x]:4}  ({anteil})")
        if not args.apply:
            print("\nNichts geschrieben. Mit --apply wiederholen.")


if __name__ == "__main__":
    asyncio.run(main())
