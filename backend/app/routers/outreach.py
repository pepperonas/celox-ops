from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models.outreach_template import OutreachTemplate
from app.models.user import User, UserRole
from app.schemas.outreach import (
    OutreachTemplateCreate,
    OutreachTemplateResponse,
    OutreachTemplateUpdate,
)
from app.services.outreach_seed import missing_templates

# Lesen: Admin UND Verkäufer (die Vorlagen sind das Werkzeug des Vertriebs).
# Schreiben: nur Admin — deshalb hängt `require_admin` an den einzelnen
# mutierenden Routen statt am Router.
#
# `get_current_user` bleibt am Router, damit `current_owner_id` für JEDE Route
# gesetzt ist. Ohne das liefen die Selects ungescopet (Tenancy-Invariante).
router = APIRouter(
    prefix="/api/outreach",
    tags=["outreach"],
    dependencies=[Depends(get_current_user)],
)


async def _require_template_reader(current_user: User = Depends(get_current_user)) -> User:
    """Lesen dürfen Admin und Verkäufer. Die übrigen Rollen bleiben ausgeschlossen
    wie bisher (das Modul war vollständig admin-only)."""
    if current_user.role not in {UserRole.admin, UserRole.verkaeufer}:
        raise HTTPException(status_code=403, detail="Adminrechte erforderlich")
    return current_user


async def _get_or_404(template_id: UUID, db: AsyncSession) -> OutreachTemplate:
    tpl = (await db.execute(
        select(OutreachTemplate).where(OutreachTemplate.id == template_id)
    )).scalar_one_or_none()
    if tpl is None:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    return tpl


@router.get("/templates", response_model=list[OutreachTemplateResponse],
            dependencies=[Depends(_require_template_reader)])
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


@router.post("/templates", dependencies=[Depends(require_admin)],
             response_model=OutreachTemplateResponse,
             status_code=status.HTTP_201_CREATED)
async def create_template(
    data: OutreachTemplateCreate, db: AsyncSession = Depends(get_db),
) -> OutreachTemplateResponse:
    tpl = OutreachTemplate(**data.model_dump())
    db.add(tpl)
    await db.flush()
    await db.refresh(tpl)
    return OutreachTemplateResponse.model_validate(tpl)


@router.put("/templates/{template_id}", response_model=OutreachTemplateResponse,
            dependencies=[Depends(require_admin)])
async def update_template(
    template_id: UUID, data: OutreachTemplateUpdate, db: AsyncSession = Depends(get_db),
) -> OutreachTemplateResponse:
    tpl = await _get_or_404(template_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tpl, key, value)
    await db.flush()
    await db.refresh(tpl)
    return OutreachTemplateResponse.model_validate(tpl)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    tpl = await _get_or_404(template_id, db)
    await db.delete(tpl)
    await db.flush()


# Kopierzähler: die EINZIGE Schreiboperation, die ein Verkäufer hier auslösen
# darf — sie ändert keinen Inhalt, nur die Statistik „wie oft benutzt".
@router.post("/templates/{template_id}/copied", response_model=OutreachTemplateResponse,
             dependencies=[Depends(_require_template_reader)])
async def mark_copied(template_id: UUID, db: AsyncSession = Depends(get_db)) -> OutreachTemplateResponse:
    """Zählt eine Nutzung (Copy) hoch — für spätere Auswertung, welche Templates konvertieren."""
    tpl = await _get_or_404(template_id, db)
    tpl.usage_count = (tpl.usage_count or 0) + 1
    await db.flush()
    await db.refresh(tpl)
    return OutreachTemplateResponse.model_validate(tpl)


@router.post("/templates/seed", response_model=list[OutreachTemplateResponse],
             dependencies=[Depends(require_admin)])
async def seed_templates(db: AsyncSession = Depends(get_db)) -> list[OutreachTemplateResponse]:
    """Legt fehlende Standard-Vorlagen an — idempotent und **additiv je Vorlage**.

    Früher lief das pro Rubrik: existierte die Rubrik, wurde nichts mehr ergänzt.
    Eine zweite Serie innerhalb einer bestehenden Rubrik hätte einen
    Arbeitsbereich damit nie erreicht (s. `missing_templates`).
    """
    def _v(x):
        return x.value if hasattr(x, "value") else x

    rows = (await db.execute(select(
        OutreachTemplate.channel, OutreachTemplate.category, OutreachTemplate.title
    ))).all()
    existing = {(_v(ch), _v(cat), title) for ch, cat, title in rows}
    added = 0
    for t in missing_templates(existing):
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
