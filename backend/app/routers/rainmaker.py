"""Rainmaker — Akquise-Aktivierungs-Modul.

Action-first Akquise-Tool: zeigt nicht "alle Kontakte", sondern was heute
konkret zu tun ist. Router wird phasenweise gefüllt:
  Phase 1: Lead-CRUD + Pipeline   ← hier
  Phase 2: Activities + "Heute"-Queue + Next-Action-Zwang
  Phase 3: Gamification (Pensum/Streak/Punkte)
  Phase 4: Reminder + Statistik
  Phase 5: Templates
"""
import math
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.rainmaker_activity import (
    RainmakerActivity,
    RainmakerActivityStatus,
)
from app.models.rainmaker_goal import DEFAULT_GOALS, RainmakerGoal
from app.models.rainmaker_lead import (
    CLOSED_STATUSES,
    RainmakerLead,
    RainmakerLeadStatus,
    RainmakerPriority,
)
from app.models.rainmaker_settings import RainmakerSettings
from app.models.rainmaker_template import RainmakerTemplate
from app.schemas.rainmaker import (
    RainmakerActivityComplete,
    RainmakerActivityCreate,
    RainmakerActivityResponse,
    RainmakerLeadCreate,
    RainmakerLeadResponse,
    RainmakerLeadSummary,
    RainmakerGoalCreate,
    RainmakerGoalProgress,
    RainmakerGoalResponse,
    RainmakerGoalUpdate,
    RainmakerLeadUpdate,
    RainmakerProgress,
    RainmakerSettingsResponse,
    RainmakerSettingsUpdate,
    RainmakerStatsResponse,
    RainmakerTemplateCreate,
    RainmakerTemplateResponse,
    RainmakerTemplateUpdate,
    RainmakerTodayItem,
    RainmakerTodayResponse,
    RmDayCount,
    RmStatusCount,
    RmTypeCount,
)
from app.services.rainmaker_service import (
    count_done_today,
    get_or_create_settings,
    get_streak_display,
    is_rotting,
    lead_response,
    planned_activities,
    priority_weight,
    register_completion,
)

router = APIRouter(
    prefix="/api/rainmaker",
    tags=["rainmaker"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/ping")
async def ping() -> dict:
    """Liveness des Rainmaker-Moduls."""
    return {"module": "rainmaker", "status": "ok"}


# --------------------------------------------------------------------------- #
#  Leads
# --------------------------------------------------------------------------- #
@router.get("/leads")
async def list_leads(
    lead_status: RainmakerLeadStatus | None = Query(None, alias="status"),
    priority: RainmakerPriority | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(RainmakerLead)
    count_query = select(func.count()).select_from(RainmakerLead)

    if lead_status:
        query = query.where(RainmakerLead.status == lead_status)
        count_query = count_query.where(RainmakerLead.status == lead_status)
    if priority:
        query = query.where(RainmakerLead.priority == priority)
        count_query = count_query.where(RainmakerLead.priority == priority)
    if search:
        like = f"%{search}%"
        cond = or_(
            RainmakerLead.company.ilike(like),
            RainmakerLead.contact_name.ilike(like),
        )
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(RainmakerLead, sort_by, RainmakerLead.created_at)
    query = query.order_by(sort_column.asc() if sort_dir == "asc" else sort_column.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    leads = (await db.execute(query)).scalars().unique().all()

    return {
        "items": [lead_response(lead) for lead in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


async def _get_lead_or_404(lead_id: uuid.UUID, db: AsyncSession) -> RainmakerLead:
    lead = (
        await db.execute(select(RainmakerLead).where(RainmakerLead.id == lead_id))
    ).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return lead


@router.get("/leads/{lead_id}", response_model=RainmakerLeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    lead = await _get_lead_or_404(lead_id, db)
    return lead_response(lead)


@router.post("/leads", response_model=RainmakerLeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: RainmakerLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    lead = RainmakerLead(**data.model_dump())
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead_response(lead)


@router.put("/leads/{lead_id}", response_model=RainmakerLeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    data: RainmakerLeadUpdate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    lead = await _get_lead_or_404(lead_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(lead, key, value)
    await db.flush()
    await db.refresh(lead)
    return lead_response(lead)


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    lead = await _get_lead_or_404(lead_id, db)
    await db.delete(lead)


# --------------------------------------------------------------------------- #
#  Activities
# --------------------------------------------------------------------------- #
@router.get("/leads/{lead_id}/activities", response_model=list[RainmakerActivityResponse])
async def list_activities(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[RainmakerActivity]:
    await _get_lead_or_404(lead_id, db)
    result = await db.execute(
        select(RainmakerActivity)
        .where(RainmakerActivity.lead_id == lead_id)
        .order_by(RainmakerActivity.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/leads/{lead_id}/activities",
    response_model=RainmakerActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_activity(
    lead_id: uuid.UUID,
    data: RainmakerActivityCreate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerActivity:
    await _get_lead_or_404(lead_id, db)
    activity = RainmakerActivity(lead_id=lead_id, **data.model_dump())
    db.add(activity)
    await db.flush()
    await db.refresh(activity)
    return activity


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    activity = (
        await db.execute(select(RainmakerActivity).where(RainmakerActivity.id == activity_id))
    ).scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Aktivität nicht gefunden")
    await db.delete(activity)


@router.post("/activities/{activity_id}/complete", response_model=RainmakerLeadResponse)
async def complete_activity(
    activity_id: uuid.UUID,
    data: RainmakerActivityComplete,
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    """Logs an activity as done. Enforces a next action UNLESS the lead is being
    closed (won/lost/dormant) — this is the 'Next-Action-Zwang'."""
    activity = (
        await db.execute(select(RainmakerActivity).where(RainmakerActivity.id == activity_id))
    ).scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Aktivität nicht gefunden")

    closing = data.close_status is not None
    if closing and data.close_status not in CLOSED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="close_status muss won, lost oder dormant sein.",
        )
    if not closing and not (data.next_type and data.next_due):
        raise HTTPException(
            status_code=400,
            detail="Nächste Aktion (Typ + Datum) ist erforderlich, sofern der Lead nicht abgeschlossen wird.",
        )

    # Mark the activity done.
    activity.status = RainmakerActivityStatus.done
    activity.completed_at = datetime.now(timezone.utc)
    if data.outcome is not None:
        activity.outcome = data.outcome
    if data.notes:
        activity.notes = data.notes

    # Gamification: award points + advance the daily-quota streak.
    await register_completion(db, activity.type)

    lead = await _get_lead_or_404(activity.lead_id, db)

    if closing:
        lead.status = data.close_status
    else:
        db.add(
            RainmakerActivity(
                lead_id=lead.id,
                type=data.next_type,
                due_date=data.next_due,
                goal_id=data.next_goal_id,
                status=RainmakerActivityStatus.planned,
            )
        )

    await db.flush()
    # Reload the activities collection so the recomputed next-action reflects the
    # just-completed activity AND the newly planned one.
    await db.refresh(lead, attribute_names=["activities"])
    return lead_response(lead)


# --------------------------------------------------------------------------- #
#  "Heute" — Activation engine
# --------------------------------------------------------------------------- #
@router.get("/today", response_model=RainmakerTodayResponse)
async def today(db: AsyncSession = Depends(get_db)) -> RainmakerTodayResponse:
    today_date = date.today()
    leads = (await db.execute(select(RainmakerLead))).scalars().unique().all()

    queue: list[RainmakerTodayItem] = []
    rotting: list[RainmakerLeadSummary] = []

    for lead in leads:
        if is_rotting(lead):
            rotting.append(RainmakerLeadSummary.model_validate(lead))
        for act in planned_activities(lead):
            if act.due_date is not None and act.due_date <= today_date:
                queue.append(
                    RainmakerTodayItem(
                        activity=RainmakerActivityResponse.model_validate(act),
                        lead=RainmakerLeadSummary.model_validate(lead),
                        days_overdue=(today_date - act.due_date).days,
                    )
                )

    # Sort: lead priority (high first), then most overdue first.
    lead_by_id = {lead.id: lead for lead in leads}
    queue.sort(
        key=lambda item: (
            priority_weight(lead_by_id[item.lead.id]),
            item.activity.due_date or today_date,
        )
    )
    rotting.sort(key=lambda s: priority_weight(lead_by_id[s.id]))

    settings = await get_or_create_settings(db)
    streak, current = await get_streak_display(db)
    progress = RainmakerProgress(
        daily_quota=settings.daily_quota,
        done_today=await count_done_today(db),
        current_streak=current,
        longest_streak=streak.longest_streak,
        total_points=streak.total_points,
        freeze_remaining=streak.freeze_remaining,
    )

    # Per-goal progress today (active goals only).
    start = datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc)
    done_by_goal_rows = (await db.execute(
        select(RainmakerActivity.goal_id, func.count())
        .where(
            RainmakerActivity.status == RainmakerActivityStatus.done,
            RainmakerActivity.completed_at >= start,
            RainmakerActivity.goal_id.isnot(None),
        )
        .group_by(RainmakerActivity.goal_id)
    )).all()
    done_by_goal = {gid: c for gid, c in done_by_goal_rows}
    active_goals = (await db.execute(
        select(RainmakerGoal)
        .where(RainmakerGoal.active.is_(True))
        .order_by(RainmakerGoal.sort_order, RainmakerGoal.created_at)
    )).scalars().all()
    goals = [
        RainmakerGoalProgress(
            id=g.id, name=g.name, suggested_type=g.suggested_type,
            daily_target=g.daily_target, done_today=int(done_by_goal.get(g.id, 0)),
        )
        for g in active_goals
    ]

    return RainmakerTodayResponse(
        date=today_date, queue=queue, rotting=rotting, progress=progress,
        goals=goals, total_leads=len(leads),
    )


# --------------------------------------------------------------------------- #
#  Statistik
# --------------------------------------------------------------------------- #
# Funnel order (active pipeline path).
_FUNNEL_ORDER = [
    RainmakerLeadStatus.new,
    RainmakerLeadStatus.contacted,
    RainmakerLeadStatus.in_conversation,
    RainmakerLeadStatus.proposal,
    RainmakerLeadStatus.won,
]


@router.get("/stats", response_model=RainmakerStatsResponse)
async def stats(db: AsyncSession = Depends(get_db)) -> RainmakerStatsResponse:
    today_date = date.today()

    # Completed activities grouped by type (last 30 days).
    since_30 = datetime.combine(today_date - timedelta(days=30), datetime.min.time(), tzinfo=timezone.utc)
    by_type_rows = (await db.execute(
        select(RainmakerActivity.type, func.count())
        .where(
            RainmakerActivity.status == RainmakerActivityStatus.done,
            RainmakerActivity.completed_at >= since_30,
        )
        .group_by(RainmakerActivity.type)
    )).all()
    activity_by_type = [RmTypeCount(type=t, count=c) for t, c in by_type_rows]

    # Completed activities per day (last 14 days, zero-filled).
    since_14 = datetime.combine(today_date - timedelta(days=13), datetime.min.time(), tzinfo=timezone.utc)
    day_col = func.date(RainmakerActivity.completed_at)
    by_day_rows = (await db.execute(
        select(day_col, func.count())
        .where(
            RainmakerActivity.status == RainmakerActivityStatus.done,
            RainmakerActivity.completed_at >= since_14,
        )
        .group_by(day_col)
    )).all()
    counts_by_day = {row[0]: row[1] for row in by_day_rows}
    activity_by_day = [
        RmDayCount(date=today_date - timedelta(days=13 - i),
                   count=int(counts_by_day.get(today_date - timedelta(days=13 - i), 0)))
        for i in range(14)
    ]

    # Funnel + totals.
    status_rows = (await db.execute(
        select(RainmakerLead.status, func.count()).group_by(RainmakerLead.status)
    )).all()
    counts_by_status = {s: c for s, c in status_rows}
    funnel = [
        RmStatusCount(status=s, count=int(counts_by_status.get(s, 0))) for s in _FUNNEL_ORDER
    ]
    total_leads = sum(int(c) for c in counts_by_status.values())
    won_count = int(counts_by_status.get(RainmakerLeadStatus.won, 0))
    lost_count = int(counts_by_status.get(RainmakerLeadStatus.lost, 0))

    open_value = (await db.execute(
        select(func.sum(RainmakerLead.value_estimate)).where(
            RainmakerLead.status.notin_(list(CLOSED_STATUSES))
        )
    )).scalar_one_or_none()
    won_value = (await db.execute(
        select(func.sum(RainmakerLead.value_estimate)).where(
            RainmakerLead.status == RainmakerLeadStatus.won
        )
    )).scalar_one_or_none()

    streak, current = await get_streak_display(db)

    return RainmakerStatsResponse(
        activity_by_type=activity_by_type,
        activity_by_day=activity_by_day,
        funnel=funnel,
        total_leads=total_leads,
        won_count=won_count,
        lost_count=lost_count,
        open_value=open_value,
        won_value=won_value,
        current_streak=current,
        longest_streak=streak.longest_streak,
        total_points=streak.total_points,
    )


# --------------------------------------------------------------------------- #
#  Settings
# --------------------------------------------------------------------------- #
@router.get("/settings", response_model=RainmakerSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> RainmakerSettings:
    return await get_or_create_settings(db)


@router.put("/settings", response_model=RainmakerSettingsResponse)
async def update_settings(
    data: RainmakerSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerSettings:
    settings_row = await get_or_create_settings(db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(settings_row, key, value)
    await db.flush()
    await db.refresh(settings_row)
    return settings_row


# --------------------------------------------------------------------------- #
#  Templates
# --------------------------------------------------------------------------- #
@router.get("/templates", response_model=list[RainmakerTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)) -> list[RainmakerTemplate]:
    result = await db.execute(
        select(RainmakerTemplate).order_by(RainmakerTemplate.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/templates", response_model=RainmakerTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: RainmakerTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerTemplate:
    tpl = RainmakerTemplate(**data.model_dump())
    db.add(tpl)
    await db.flush()
    await db.refresh(tpl)
    return tpl


@router.put("/templates/{template_id}", response_model=RainmakerTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: RainmakerTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerTemplate:
    tpl = (
        await db.execute(select(RainmakerTemplate).where(RainmakerTemplate.id == template_id))
    ).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tpl, key, value)
    await db.flush()
    await db.refresh(tpl)
    return tpl


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    tpl = (
        await db.execute(select(RainmakerTemplate).where(RainmakerTemplate.id == template_id))
    ).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    await db.delete(tpl)


# --------------------------------------------------------------------------- #
#  Goals (Akquise-Ziele)
# --------------------------------------------------------------------------- #
@router.get("/goals", response_model=list[RainmakerGoalResponse])
async def list_goals(db: AsyncSession = Depends(get_db)) -> list[RainmakerGoal]:
    result = await db.execute(
        select(RainmakerGoal).order_by(RainmakerGoal.sort_order, RainmakerGoal.created_at)
    )
    return list(result.scalars().all())


@router.post("/goals", response_model=RainmakerGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: RainmakerGoalCreate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerGoal:
    goal = RainmakerGoal(**data.model_dump())
    db.add(goal)
    await db.flush()
    await db.refresh(goal)
    return goal


@router.post("/goals/seed", response_model=list[RainmakerGoalResponse])
async def seed_goals(db: AsyncSession = Depends(get_db)) -> list[RainmakerGoal]:
    """Seed the default goal set — idempotent (only seeds when none exist)."""
    existing = (await db.execute(select(func.count()).select_from(RainmakerGoal))).scalar_one()
    if existing == 0:
        for i, (name, suggested_type, daily_target) in enumerate(DEFAULT_GOALS):
            db.add(RainmakerGoal(name=name, suggested_type=suggested_type, daily_target=daily_target, sort_order=i))
        await db.flush()
    result = await db.execute(
        select(RainmakerGoal).order_by(RainmakerGoal.sort_order, RainmakerGoal.created_at)
    )
    return list(result.scalars().all())


@router.put("/goals/{goal_id}", response_model=RainmakerGoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    data: RainmakerGoalUpdate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerGoal:
    goal = (
        await db.execute(select(RainmakerGoal).where(RainmakerGoal.id == goal_id))
    ).scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Ziel nicht gefunden")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    await db.flush()
    await db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    goal = (
        await db.execute(select(RainmakerGoal).where(RainmakerGoal.id == goal_id))
    ).scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Ziel nicht gefunden")
    await db.delete(goal)
