"""iCal-Export aller Termine und Fristen — abonnierbar in Mac/iOS-Kalender."""
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import get_db
from app.models.contract import Contract, ContractStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User, workspace_owner_id
from app.tenancy import current_owner_id

router = APIRouter(prefix="/api/ical", tags=["ical"])


def _esc(s: str) -> str:
    """iCal text escape."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _uid(prefix: str, key: str) -> str:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{h}@celox.io"


@router.get("")
async def ical_feed(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Public per-user iCal feed (no JWT — protected by the user's personal `token`).
    Subscribe to: https://ops.celox.io/api/ical?token=<user.ical_token>
    The token identifies the user; the feed is then scoped to that user's data only.
    """
    if not token:
        return Response(status_code=403, content="Forbidden")
    user = (await db.execute(select(User).where(User.ical_token == token))).scalar_one_or_none()
    if user is None or not user.is_active:
        return Response(status_code=403, content="Forbidden")
    # Scope all following ORM queries to this user (multi-tenant isolation).
    # Gleicher Arbeitsbereich wie im UI (Mitarbeitende sehen den des Chefs).
    current_owner_id.set(workspace_owner_id(user))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//celox ops//{settings.BUSINESS_NAME or 'celox'}//DE",
        f"X-WR-CALNAME:{_esc(settings.BUSINESS_NAME or 'celox ops')} — Fristen",
        "X-WR-TIMEZONE:Europe/Berlin",
        "CALSCALE:GREGORIAN",
    ]

    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Invoice due dates
    res = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.status.in_([InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig]))
    )
    for inv in res.scalars().all():
        if not inv.due_date:
            continue
        cust_name = inv.customer.name if inv.customer else ""
        lines += [
            "BEGIN:VEVENT",
            f"UID:{_uid('inv', str(inv.id))}",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{inv.due_date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(inv.due_date + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_esc(f'Rechnung fällig: {inv.invoice_number} — {cust_name}')}",
            f"DESCRIPTION:{_esc(f'{inv.title} · {float(inv.total):.2f} EUR · Status: {inv.status.value}')}",
            "CATEGORIES:Rechnung",
            "END:VEVENT",
        ]

    # Contract end dates
    res = await db.execute(
        select(Contract)
        .options(joinedload(Contract.customer))
        .where(Contract.status == ContractStatus.aktiv)
        .where(Contract.end_date.is_not(None))
    )
    for con in res.scalars().all():
        if not con.end_date:
            continue
        cust_name = con.customer.name if con.customer else ""
        lines += [
            "BEGIN:VEVENT",
            f"UID:{_uid('con', str(con.id))}",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{con.end_date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(con.end_date + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_esc(f'Vertragsende: {con.title} — {cust_name}')}",
            f"DESCRIPTION:{_esc(f'Typ: {con.type.value} · Monatlich: {float(con.monthly_amount):.2f} EUR')}",
            "CATEGORIES:Vertrag",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="celox-ops.ics"'},
    )
