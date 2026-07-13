"""Einmaliges Backfill: setzt `email_status` für alle Bestands-Leads mit E-Mail
(SMTP-frei, nur DNS/MX). Owner-übergreifend (ContextVar ungesetzt ⇒ global).

    docker compose exec backend python -m app.scripts.backfill_email_status
"""
import asyncio

import app.main  # noqa: F401  — registriert alle Modelle + Tenancy-Events
from sqlalchemy import select

from app.database import async_session_factory
from app.models.rainmaker_lead import RainmakerLead
from app.services.email_verifier import verify_email


async def main() -> None:
    async with async_session_factory() as db:
        leads = list((await db.execute(
            select(RainmakerLead).where(
                RainmakerLead.email.isnot(None), RainmakerLead.email != "")
        )).scalars().all())
        cache: dict = {}
        counts: dict[str, int] = {}
        for lead in leads:
            st = (await verify_email(lead.email, mx_cache=cache)).status.value
            lead.email_status = st
            counts[st] = counts.get(st, 0) + 1
        await db.commit()
        print(f"Backfill: {len(leads)} Leads mit E-Mail geprüft → {counts}")


if __name__ == "__main__":
    asyncio.run(main())
