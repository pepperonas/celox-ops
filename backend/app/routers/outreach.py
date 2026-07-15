from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models.outreach_template import OutreachTemplate
from app.schemas.outreach import (
    OutreachTemplateCreate,
    OutreachTemplateResponse,
    OutreachTemplateUpdate,
)
from app.services.outreach_seed import default_templates

# Admin-only Modul (owner-scoped über die Tenancy-Events; require_admin setzt den
# current_owner_id via get_current_user).
router = APIRouter(
    prefix="/api/outreach",
    tags=["outreach"],
    dependencies=[Depends(require_admin)],
)


async def _get_or_404(template_id: UUID, db: AsyncSession) -> OutreachTemplate:
    tpl = (await db.execute(
        select(OutreachTemplate).where(OutreachTemplate.id == template_id)
    )).scalar_one_or_none()
    if tpl is None:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    return tpl


@router.get("/templates", response_model=list[OutreachTemplateResponse])
async def list_templates(
    channel: str | None = None,
    category: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[OutreachTemplateResponse]:
    """Alle Templates des Owners (plain list, die UI filtert client-seitig).
    Optionale Serverfilter: channel, category, q (Volltext über Titel/Betreff/Body)."""
    query = select(OutreachTemplate).order_by(
        OutreachTemplate.category, OutreachTemplate.sort_order, OutreachTemplate.title
    )
    if channel:
        query = query.where(OutreachTemplate.channel == channel)
    if category:
        query = query.where(OutreachTemplate.category == category)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(
            OutreachTemplate.title.ilike(like),
            OutreachTemplate.subject.ilike(like),
            OutreachTemplate.body.ilike(like),
        ))
    rows = (await db.execute(query)).scalars().all()
    return [OutreachTemplateResponse.model_validate(t) for t in rows]


@router.post("/templates", response_model=OutreachTemplateResponse,
             status_code=status.HTTP_201_CREATED)
async def create_template(
    data: OutreachTemplateCreate, db: AsyncSession = Depends(get_db),
) -> OutreachTemplateResponse:
    tpl = OutreachTemplate(**data.model_dump())
    db.add(tpl)
    await db.flush()
    await db.refresh(tpl)
    return OutreachTemplateResponse.model_validate(tpl)


@router.put("/templates/{template_id}", response_model=OutreachTemplateResponse)
async def update_template(
    template_id: UUID, data: OutreachTemplateUpdate, db: AsyncSession = Depends(get_db),
) -> OutreachTemplateResponse:
    tpl = await _get_or_404(template_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tpl, key, value)
    await db.flush()
    await db.refresh(tpl)
    return OutreachTemplateResponse.model_validate(tpl)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    tpl = await _get_or_404(template_id, db)
    await db.delete(tpl)
    await db.flush()


@router.post("/templates/{template_id}/copied", response_model=OutreachTemplateResponse)
async def mark_copied(template_id: UUID, db: AsyncSession = Depends(get_db)) -> OutreachTemplateResponse:
    """Zählt eine Nutzung (Copy) hoch — für spätere Auswertung, welche Templates konvertieren."""
    tpl = await _get_or_404(template_id, db)
    tpl.usage_count = (tpl.usage_count or 0) + 1
    await db.flush()
    await db.refresh(tpl)
    return OutreachTemplateResponse.model_validate(tpl)


@router.post("/templates/seed", response_model=list[OutreachTemplateResponse])
async def seed_templates(db: AsyncSession = Depends(get_db)) -> list[OutreachTemplateResponse]:
    """Legt fehlende Standard-Rubriken an — idempotent und **additiv**: fehlt eine
    ganze Rubrik (z. B. eine neu ergänzte Linie), wird nur diese nachgezogen; das
    fügt bestehenden Nutzern neue Vorlagen zu, ohne Duplikate."""
    existing_cats = {
        (c.value if hasattr(c, "value") else c)
        for c in (await db.execute(select(OutreachTemplate.category).distinct())).scalars().all()
    }
    added = 0
    for t in default_templates():
        if t["category"] not in existing_cats:
            db.add(OutreachTemplate(**t))
            added += 1
    if added:
        await db.flush()
    rows = (await db.execute(
        select(OutreachTemplate).order_by(
            OutreachTemplate.category, OutreachTemplate.sort_order, OutreachTemplate.title
        )
    )).scalars().all()
    return [OutreachTemplateResponse.model_validate(t) for t in rows]
