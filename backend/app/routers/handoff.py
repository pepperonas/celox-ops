"""Kunde übergeben an portal.celox.io / datenschutz.celox.io (Kontrakt §6.2).

Push, Einmal-Kopie, idempotenter Re-Push (Enrich-only auf Zielseite). Kein
Retry-Automat, kein Hintergrund-Sync — Fehler landen lesbar in der UI, der
Re-Push ist idempotent (external_ref = customers.id).
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.user import User
from app.services.handoff_service import (
    HandoffError,
    build_datenschutz_customer,
    build_envelope,
    build_portal_customer,
    field_keys,
    parse_address,
    send_handoff,
)

logger = logging.getLogger(__name__)

# Router-level Auth wie in allen anderen Routern (Belt-and-braces: die Endpoints
# brauchen get_current_user zusätzlich als Param für Username + Owner-Scoping —
# FastAPI cached die Dependency, sie läuft trotzdem nur einmal pro Request).
router = APIRouter(
    prefix="/api/customers",
    tags=["handoff"],
    dependencies=[Depends(get_current_user)],
)

_TARGET_CONFIG = {
    "portal": lambda: (settings.PORTAL_HANDOFF_BASE_URL, settings.PORTAL_HANDOFF_KEY),
    "datenschutz": lambda: (settings.DATENSCHUTZ_HANDOFF_BASE_URL, settings.DATENSCHUTZ_HANDOFF_KEY),
}
_STATUS_COLUMN = {"portal": "portal_handoff", "datenschutz": "datenschutz_handoff"}


class HandoffRequest(BaseModel):
    target: Literal["portal", "datenschutz"]
    # portal-Optionen
    entitlements: list[str] = Field(default_factory=list)
    send_onboarding: bool = False
    # datenschutz-Option
    invite_contact: bool = True


async def _load_customer(customer_id: uuid.UUID, db: AsyncSession) -> Customer:
    """Owner-scoped Load (Tenancy-Invariante: scoped select vor Nutzung)."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return customer


def _parse_status(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


@router.get("/{customer_id}/handoff")
async def handoff_status(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Status beider Ziele + Laufzeit-Konfig für die UI (Buttons nur bei
    konfigurierter Base-URL) + serverseitige Adress-Vorschau (§6.3-Parser —
    kein dupliziertes Parsing im Frontend)."""
    customer = await _load_customer(customer_id, db)
    return {
        "email_missing": not (customer.email or "").strip(),
        "portal": {
            "configured": bool(settings.PORTAL_HANDOFF_BASE_URL),
            "status": _parse_status(customer.portal_handoff),
        },
        "datenschutz": {
            "configured": bool(settings.DATENSCHUTZ_HANDOFF_BASE_URL),
            "status": _parse_status(customer.datenschutz_handoff),
            "address_preview": parse_address(customer.address),
        },
    }


async def _write_audit(
    db: AsyncSession, username: str, customer_id: uuid.UUID, detail: dict
) -> None:
    """Fachlicher Audit-Eintrag (§6.5) — zusätzlich zur AuditMiddleware.
    Best-effort in der laufenden Session (commit macht der Aufrufer)."""
    db.add(
        AuditLog(
            user=username,
            action="customer.handoff",
            path=f"/api/customers/{customer_id}/handoff",
            entity_type="customers",
            entity_id=str(customer_id),
            status_code=detail.get("http_status", 200),
            detail=json.dumps(detail, ensure_ascii=False),
        )
    )


@router.post("/{customer_id}/handoff")
async def push_handoff(
    customer_id: uuid.UUID,
    body: HandoffRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    base_url, key = _TARGET_CONFIG[body.target]()
    if not base_url or not key:
        raise HTTPException(
            status_code=503,
            detail=f"Handoff-Ziel „{body.target}“ ist nicht konfiguriert.",
        )

    customer = await _load_customer(customer_id, db)
    if not (customer.email or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Ohne E-Mail-Adresse ist keine Übergabe möglich — bitte zuerst am Kunden pflegen.",
        )

    if body.target == "portal":
        customer_obj = build_portal_customer(
            customer,
            entitlements=body.entitlements,
            send_onboarding=body.send_onboarding,
        )
    else:
        customer_obj = build_datenschutz_customer(
            customer, invite_contact=body.invite_contact
        )

    envelope = build_envelope(customer.id, customer_obj)
    keys = field_keys(customer_obj)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    column = _STATUS_COLUMN[body.target]

    try:
        result = await send_handoff(base_url, key, envelope)
    except HandoffError as e:
        # Fehler-Status persistieren (§6.4: last_status = "error:<code>") + Audit
        prev = _parse_status(getattr(customer, column)) or {}
        prev.update(
            {
                "last_handoff_at": now,
                "last_status": f"error:{e.code}",
                "handoff_id": envelope["handoff_id"],
            }
        )
        setattr(customer, column, json.dumps(prev, ensure_ascii=False))
        await _write_audit(
            db,
            user.username,
            customer.id,
            {
                "target": body.target,
                "handoff_id": envelope["handoff_id"],
                "fields": keys,
                "result": f"error:{e.code}",
                "http_status": e.status,
            },
        )
        await db.commit()
        raise HTTPException(status_code=e.status, detail=e.detail)

    created = bool(result.get("created"))
    status_json = {
        "target_id": str(result.get("company_id") or result.get("tenant_id") or ""),
        "external_ref_confirmed": True,
        "last_handoff_at": now,
        "last_status": "created" if created else "updated",
        "handoff_id": envelope["handoff_id"],
    }
    setattr(customer, column, json.dumps(status_json, ensure_ascii=False))
    await _write_audit(
        db,
        user.username,
        customer.id,
        {
            "target": body.target,
            "handoff_id": envelope["handoff_id"],
            "fields": keys,
            "result": status_json["last_status"],
            "http_status": 200,
        },
    )
    await db.commit()
    logger.info(
        "Handoff %s → %s: %s (handoff_id=%s)",
        customer.id,
        body.target,
        status_json["last_status"],
        envelope["handoff_id"],
    )
    return {
        "ok": True,
        "created": created,
        "target": body.target,
        "status": status_json,
        # Nie Credentials durchreichen (Kontrakt §0 letzte Zeile) — die
        # Ziel-Response enthält sie ohnehin nicht.
        "onboarding_sent": bool(result.get("onboarding_sent")),
        "invitation_sent": bool(result.get("invitation_sent")),
    }
