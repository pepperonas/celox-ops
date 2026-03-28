import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityResponse

router = APIRouter(
    prefix="/api/activities",
    tags=["activities"],
    dependencies=[Depends(get_current_user)],
)

MANUAL_TYPES = {"note", "call", "email", "meeting"}


@router.get("")
async def list_activities(
    customer_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Activity).where(Activity.customer_id == customer_id)
    count_query = select(func.count()).select_from(Activity).where(
        Activity.customer_id == customer_id
    )

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Activity.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    activities = result.scalars().all()

    return {
        "items": [ActivityResponse.model_validate(a) for a in activities],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    data: ActivityCreate,
    db: AsyncSession = Depends(get_db),
) -> ActivityResponse:
    if data.type not in MANUAL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Manuell erstellbare Typen: {', '.join(sorted(MANUAL_TYPES))}",
        )

    activity = Activity(
        customer_id=data.customer_id,
        type=data.type,
        title=data.title,
        description=data.description,
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)

    return ActivityResponse.model_validate(activity)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Aktivität nicht gefunden")

    if activity.type not in MANUAL_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Automatisch erstellte Einträge können nicht gelöscht werden",
        )

    await db.delete(activity)
