"""Einmalige Übernahme: `ANTHROPIC_API_KEY` aus der `.env` → Arbeitsbereich.

Der Schlüssel lag global in der `.env` und galt für alle. Seit der Umstellung
rechnet jeder Bereichs-Inhaber über seinen eigenen ab (`app_settings`). Dieses
Skript hängt den bestehenden Schlüssel an **einen** Arbeitsbereich, damit der
Betrieb nicht unterbricht.

    python -m app.scripts.adopt_env_anthropic_key --user martinpaush@gmail.com [--apply]

Der Benutzer wird über `google_email`, `email` oder `username` gefunden und MUSS
Bereichs-Inhaber sein (`works_for_id IS NULL`) — Mitarbeitende haben keinen
eigenen Schlüssel, sie nutzen den ihres Inhabers.

**Der Schlüssel wird nie ausgegeben** (nur maskiert), damit er nicht in Logs,
Shell-Historie oder Terminalmitschnitten landet. Default ist ein Trockenlauf.
"""
import argparse
import asyncio
import sys

from sqlalchemy import or_, select

from app.config import settings
from app.database import async_session_factory
from app.models.user import User
from app.services.places_usage import mask_key
from app.tenancy import current_owner_id


async def run(identifier: str, apply: bool) -> int:
    from app.models.app_settings import AppSettings

    env_key = (settings.ANTHROPIC_API_KEY or "").strip()
    if not env_key:
        print("FEHLER: ANTHROPIC_API_KEY ist in der Umgebung nicht gesetzt — "
              "nichts zu übernehmen.")
        return 2

    needle = identifier.strip().lower()
    async with async_session_factory() as db:
        # Ohne gesetzten ContextVar sind Selects global — hier gewollt, das
        # Skript sucht ja über alle Bereiche hinweg.
        user = (await db.execute(
            select(User).where(or_(
                User.google_email.ilike(needle),
                User.email.ilike(needle),
                User.username.ilike(needle),
            )).limit(1)
        )).scalar_one_or_none()
        if user is None:
            print(f"FEHLER: kein Benutzer zu '{identifier}' gefunden.")
            return 2
        if user.works_for_id is not None:
            print(f"FEHLER: '{user.username}' ist Mitarbeitende(r) in einem fremden "
                  "Arbeitsbereich und hat keinen eigenen Schlüssel. "
                  "Bitte den Bereichs-Inhaber angeben.")
            return 2

        # Ab hier im Bereich des Nutzers arbeiten (owner_id wird gestempelt).
        token = current_owner_id.set(user.id)
        try:
            row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
            existing = (row.anthropic_api_key or "").strip() if row else ""
            print(f"Arbeitsbereich : {user.username} ({user.google_email or user.email or '—'})")
            print(f"Bisher hinterlegt: {mask_key(existing) if existing else '— (keiner)'}")
            print(f"Aus der .env     : {mask_key(env_key)}")

            if existing == env_key:
                print("Bereits identisch — nichts zu tun.")
                return 0
            if existing and not apply:
                print("HINWEIS: es ist schon ein anderer Schlüssel hinterlegt; "
                      "--apply würde ihn überschreiben.")
            if not apply:
                print("\nTrockenlauf. Mit --apply wirklich übernehmen.")
                return 0

            if row is None:
                row = AppSettings()
                db.add(row)
                await db.flush()
            row.anthropic_api_key = env_key
            await db.commit()
            print("\nÜbernommen. Der Bereich rechnet jetzt über seinen eigenen Schlüssel ab.")
            return 0
        finally:
            current_owner_id.reset(token)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True,
                        help="google_email, email oder username des Bereichs-Inhabers")
    parser.add_argument("--apply", action="store_true",
                        help="wirklich schreiben (ohne: Trockenlauf)")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.user, args.apply)))


if __name__ == "__main__":
    main()
