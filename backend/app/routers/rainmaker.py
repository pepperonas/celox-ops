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
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.rainmaker_activity import (
    RainmakerActivity,
    RainmakerActivityStatus,
    RainmakerActivityType,
)
from app.models.rainmaker_goal import DEFAULT_GOALS, RainmakerGoal
from app.models.rainmaker_lead import (
    CLOSED_STATUSES,
    RainmakerLead,
    RainmakerLeadStatus,
    RainmakerPriority,
)
from app.models.rainmaker_settings import RainmakerDreamMode, RainmakerSettings
from app.models.rainmaker_template import RainmakerTemplate
from app.schemas.rainmaker import (
    DiscoveredCandidate,
    LeadDiscoveryImportRequest,
    LeadDiscoveryRequest,
    LeadDiscoveryResult,
    LinkedInImportRequest,
    LinkedInImportResult,
    LinkedInPreviewRow,
    RainmakerActivityComplete,
    RainmakerActivityCreate,
    RainmakerActivityResponse,
    RainmakerDreamResponse,
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
from app.config import settings
from app.services.lead_discovery import discover_google, discover_osm
from app.services.linkedin_import import (
    normalize_profile_url,
    parse_linkedin_archive,
    parse_linkedin_connections,
    row_to_lead_fields,
)
from app.services.rainmaker_service import (
    DREAM_EV_WEIGHTS,
    count_done_today,
    dream_activities_ev,
    dream_ev_per_contact,
    dream_projected_date,
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
#  LinkedIn-Import (offizieller Connections.csv-Datenexport — keine API)
# --------------------------------------------------------------------------- #
_LINKEDIN_IMPORT_MAX_BYTES = 10 * 1024 * 1024
_LINKEDIN_IMPORT_MAX_ROWS = 20_000


def _norm_url(url: str | None) -> str | None:
    u = (url or "").strip().rstrip("/").lower()
    return u.removeprefix("https://").removeprefix("http://").removeprefix("www.") or None


async def _lead_dedup_keys(db: AsyncSession) -> tuple[set, set]:
    """(URL-Keys, Namens-Keys) der bestehenden Leads des Owners — für die
    Duplikat-Erkennung. Query ist via Tenancy-Events automatisch owner-scoped."""
    res = await db.execute(select(RainmakerLead.website, RainmakerLead.contact_name, RainmakerLead.company))
    urls, names = set(), set()
    for website, contact_name, company in res.all():
        if u := _norm_url(website):
            urls.add(u)
        # Sowohl Ansprechpartner- als auch Firmenname aufnehmen: Discovery-Leads
        # führen den Firmennamen in company (contact_name leer), LinkedIn den
        # Personennamen in contact_name — beide müssen dedupen.
        if n := (contact_name or "").strip().lower():
            names.add(n)
        if c := (company or "").strip().lower():
            names.add(c)
    return urls, names


def _row_keys(first_name: str, last_name: str, url: str) -> tuple[str | None, str]:
    return _norm_url(url), f"{first_name} {last_name}".strip().lower()


@router.post("/import/linkedin/preview", response_model=list[LinkedInPreviewRow])
async def linkedin_import_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> list[LinkedInPreviewRow]:
    """Parst den LinkedIn-Export (komplettes ZIP-Archiv ODER einzelne
    Connections.csv) und markiert Duplikate. Aus dem ZIP werden zusätzlich
    offene ausgehende Kontaktanfragen (Invitations.csv → Status 'contacted')
    und der Nachrichtenverlauf (messages.csv → Status 'in_conversation' +
    Nachrichten für erledigte Aktivitäten) gezogen. Legt noch nichts an."""
    raw = await file.read()
    if len(raw) > _LINKEDIN_IMPORT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Datei zu groß (max. 10 MB)")

    invitations: list[dict] = []
    messages: dict[str, dict] = {}
    try:
        if raw[:2] == b"PK":  # ZIP-Archiv (kompletter Export)
            archive = parse_linkedin_archive(raw)
            rows = archive["connections"]
            invitations = archive["invitations"]
            messages = archive["messages"]
        else:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            rows = parse_linkedin_connections(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if len(rows) + len(invitations) > _LINKEDIN_IMPORT_MAX_ROWS:
        raise HTTPException(status_code=413, detail="Zu viele Zeilen (max. 20.000)")

    urls, names = await _lead_dedup_keys(db)
    seen_in_file: set[str] = set()
    out: list[LinkedInPreviewRow] = []

    def _is_duplicate(url_key: str | None, name_key: str) -> bool:
        file_key = url_key or name_key
        dup = (
            (url_key is not None and url_key in urls)
            or (bool(name_key) and name_key in names)
            or file_key in seen_in_file
        )
        seen_in_file.add(file_key)
        return dup

    # Bestätigte Kontakte — mit Nachrichtenverlauf angereichert
    for r in rows:
        url_key, name_key = _row_keys(r["first_name"], r["last_name"], r["url"])
        msg = messages.get(normalize_profile_url(r["url"]), None) if r["url"] else None
        out.append(LinkedInPreviewRow(
            **r,
            source="connection",
            status=RainmakerLeadStatus.in_conversation if msg else RainmakerLeadStatus.connected,
            message_count=msg["count"] if msg else 0,
            last_message_at=msg["last_date"] if msg else "",
            messages=msg["messages"] if msg else [],
            duplicate=_is_duplicate(url_key, name_key),
        ))

    # Offene ausgehende Kontaktanfragen (nicht in Connections → noch unbeantwortet)
    connection_urls = {normalize_profile_url(r["url"]) for r in rows if r["url"]}
    for inv in invitations:
        inv_url = normalize_profile_url(inv["url"])
        if inv_url and inv_url in connection_urls:
            continue  # inzwischen angenommen → ist als Connection drin
        parts = inv["name"].split(" ", 1)
        first, last = parts[0], (parts[1] if len(parts) > 1 else "")
        url_key, name_key = _row_keys(first, last, inv["url"])
        msg = messages.get(inv_url, None) if inv_url else None
        out.append(LinkedInPreviewRow(
            first_name=first,
            last_name=last,
            url=inv["url"],
            source="invitation",
            status=RainmakerLeadStatus.in_conversation if msg else RainmakerLeadStatus.contacted,
            invited_at=inv["sent_at"],
            message_count=msg["count"] if msg else 0,
            last_message_at=msg["last_date"] if msg else "",
            messages=msg["messages"] if msg else [],
            duplicate=_is_duplicate(url_key, name_key),
        ))
    return out


@router.post("/import/linkedin", response_model=LinkedInImportResult)
async def linkedin_import(
    data: LinkedInImportRequest,
    db: AsyncSession = Depends(get_db),
) -> LinkedInImportResult:
    """Legt die (im Frontend ausgewählten) Zeilen als Leads an — mit dem
    vorgeschlagenen Status und dem Nachrichtenverlauf als ERLEDIGTE
    Aktivitäten (historisches Datum, bewusst OHNE Punkte-/Streak-Gutschrift).
    Duplikate werden nicht doppelt angelegt, sondern ANGEREICHERT: Status-
    Upgrade (new → contacted → in_conversation, nie über offene Verhandlungs-/
    Abschluss-Status hinweg), fehlende Felder (E-Mail/Funktion/Website)
    nachgetragen, Nachrichtenverlauf nachgezogen, falls noch keiner am Lead
    hängt — so verliert ein erneuter Upload eines reichhaltigeren Exports
    keine Informationen."""
    if len(data.rows) > _LINKEDIN_IMPORT_MAX_ROWS:
        raise HTTPException(status_code=413, detail="Zu viele Zeilen (max. 20.000)")

    # Lead-Lookup für Enrichment (owner-scoped via Tenancy-Events)
    existing = (await db.execute(select(RainmakerLead))).scalars().all()
    url_map: dict[str, RainmakerLead] = {}
    name_map: dict[str, RainmakerLead] = {}
    for lead in existing:
        if u := _norm_url(lead.website):
            url_map[u] = lead
        if n := (lead.contact_name or "").strip().lower():
            name_map[n] = lead

    _status_rank = {
        RainmakerLeadStatus.new: 0,
        RainmakerLeadStatus.contacted: 1,
        RainmakerLeadStatus.connected: 2,
        RainmakerLeadStatus.in_conversation: 3,
    }

    created = skipped = enriched = activities_created = 0
    for row in data.rows:
        fields = row_to_lead_fields(row.model_dump())
        url_key, name_key = _row_keys(row.first_name, row.last_name, row.url)
        existing_lead = (url_map.get(url_key) if url_key else None) or name_map.get(name_key)
        if existing_lead is not None:
            changed = False
            # Status nur AUFwerten und nur solange der Lead im Frühstadium ist
            cur_rank = _status_rank.get(existing_lead.status)
            new_rank = _status_rank.get(row.status)
            if cur_rank is not None and new_rank is not None and new_rank > cur_rank:
                existing_lead.status = row.status
                changed = True
            # Fehlende Felder nachtragen
            if not existing_lead.email and fields.get("email"):
                existing_lead.email = fields["email"]
                changed = True
            if not existing_lead.role and fields.get("role"):
                existing_lead.role = fields["role"]
                changed = True
            if not existing_lead.website and fields.get("website"):
                existing_lead.website = fields["website"]
                changed = True
            # Nachrichtenverlauf nachziehen, falls noch keiner importiert wurde
            if row.messages:
                has_linkedin_msgs = (
                    await db.execute(
                        select(func.count()).select_from(RainmakerActivity).where(
                            RainmakerActivity.lead_id == existing_lead.id,
                            RainmakerActivity.notes.like("[LinkedIn%"),
                        )
                    )
                ).scalar_one()
                if not has_linkedin_msgs:
                    for msg in row.messages[:50]:
                        db.add(RainmakerActivity(
                            lead_id=existing_lead.id,
                            type=RainmakerActivityType.message,
                            status=RainmakerActivityStatus.done,
                            completed_at=_parse_linkedin_datetime(msg.date),
                            notes=f"[LinkedIn, {msg.direction}] {msg.snippet}"[:2000],
                        ))
                        activities_created += 1
                    changed = True
            if changed:
                enriched += 1
            else:
                skipped += 1
            continue
        if row.source == "invitation":
            note = "LinkedIn-Kontaktanfrage gesendet"
            if row.invited_at:
                note += f" am {row.invited_at}"
            note += " (noch nicht angenommen)"
            fields["notes"] = note
        fields["status"] = row.status
        lead = RainmakerLead(**fields)
        db.add(lead)
        await db.flush()  # lead.id für Aktivitäten

        # Nachrichtenverlauf als erledigte Aktivitäten (ohne Gamification)
        for msg in row.messages[:50]:
            completed = _parse_linkedin_datetime(msg.date)
            db.add(RainmakerActivity(
                lead_id=lead.id,
                type=RainmakerActivityType.message,
                status=RainmakerActivityStatus.done,
                completed_at=completed,
                notes=f"[LinkedIn, {msg.direction}] {msg.snippet}"[:2000],
            ))
            activities_created += 1

        # Neu angelegte Leads in die Lookup-Maps — Mehrfachzeilen derselben
        # Person innerhalb eines Batches werden so angereichert statt dupliziert
        if url_key:
            url_map[url_key] = lead
        if name_key:
            name_map[name_key] = lead
        created += 1
    await db.flush()
    return LinkedInImportResult(
        created=created,
        skipped_duplicates=skipped,
        enriched=enriched,
        activities_created=activities_created,
    )


def _parse_linkedin_datetime(value: str) -> datetime | None:
    """'2026-07-08 23:03:13 UTC' → aware datetime; None bei Unlesbarem."""
    v = (value or "").strip().removesuffix(" UTC")
    try:
        return datetime.strptime(v, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
#  Lead-Discovery (automatische Suche: OpenStreetMap + optional Google Places)
# --------------------------------------------------------------------------- #
def _candidate_keys(name: str, website: str | None) -> tuple[str | None, str]:
    return _norm_url(website), (name or "").strip().lower()


@router.post("/discover/preview", response_model=list[DiscoveredCandidate])
async def discover_preview(
    data: LeadDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
) -> list[DiscoveredCandidate]:
    """Sucht Firmen nach Branche + Ort und markiert Duplikate (bereits als Lead
    vorhanden, per Website-Domain oder Firmenname; owner-scoped). Legt nichts an."""
    import httpx

    from app.models.app_settings import AppSettings
    from app.services.places_usage import bump

    app_row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    # Pro-Workspace-Key hat Vorrang, sonst globale env-Variable.
    places_key = (app_row.google_places_api_key if app_row else None) or settings.GOOGLE_PLACES_API_KEY

    try:
        async with httpx.AsyncClient(timeout=40, headers={"User-Agent": "celox-ops-rainmaker/1.0"}) as client:
            if data.source == "google":
                if not places_key:
                    raise HTTPException(status_code=503, detail="Google Places ist nicht konfiguriert — API-Key in den Einstellungen hinterlegen.")
                candidates = await discover_google(data.category, data.location, data.limit, places_key, client)
                # Eigenen Nutzungszähler hochzählen (nur bei echter Google-Suche).
                if app_row is not None:
                    app_row.google_places_period, app_row.google_places_calls = bump(
                        app_row.google_places_period, app_row.google_places_calls)
            else:
                candidates = await discover_osm(data.category, data.location, data.limit, client)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Suche fehlgeschlagen: {exc}")

    urls, names = await _lead_dedup_keys(db)
    seen: set[str] = set()
    out: list[DiscoveredCandidate] = []
    for c in candidates:
        url_key, name_key = _candidate_keys(c["name"], c.get("website"))
        file_key = url_key or name_key
        dup = ((url_key is not None and url_key in urls)
               or (bool(name_key) and name_key in names)
               or file_key in seen)
        seen.add(file_key)
        out.append(DiscoveredCandidate(**c, duplicate=dup))
    return out


@router.post("/discover/import", response_model=LeadDiscoveryResult)
async def discover_import(
    data: LeadDiscoveryImportRequest,
    db: AsyncSession = Depends(get_db),
) -> LeadDiscoveryResult:
    """Legt die ausgewählten Kandidaten als Leads an (Status 'new'), mit Quelle
    und owner-scoped Dedup-Wiederprüfung (Doppel-Submit-sicher)."""
    if len(data.rows) > 5000:
        raise HTTPException(status_code=413, detail="Zu viele Kandidaten (max. 5000)")
    urls, names = await _lead_dedup_keys(db)
    created = skipped = 0
    tags = ["discovery"]
    if data.segment:
        tags.append(data.segment)
    for c in data.rows:
        url_key, name_key = _candidate_keys(c.name, c.website)
        if (url_key is not None and url_key in urls) or (bool(name_key) and name_key in names):
            skipped += 1
            continue
        db.add(RainmakerLead(
            company=(c.name or "").strip()[:255] or "Unbenannt",
            website=(c.website or "").strip()[:500] or None,
            phone=(c.phone or "").strip()[:50] or None,
            address=(c.address or "").strip() or None,
            source=c.source,
            status=RainmakerLeadStatus.new,
            tags=tags,
            notes=f"Automatisch gefunden ({c.source})" + (f" · Ref {c.source_ref}" if c.source_ref else ""),
        ))
        if url_key:
            urls.add(url_key)
        if name_key:
            names.add(name_key)
        created += 1
    await db.flush()
    return LeadDiscoveryResult(created=created, skipped_duplicates=skipped)


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
    RainmakerLeadStatus.connected,
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
#  Traumziel — expected-value motivation engine
# --------------------------------------------------------------------------- #
_DREAM_DEFAULT_NAME = "Porsche Cayenne Turbo Electric"


@router.get("/dream", response_model=RainmakerDreamResponse)
async def dream(db: AsyncSession = Depends(get_db)) -> RainmakerDreamResponse:
    """Progress toward the dream goal. In "ev" mode every completed action since
    the start date carries its statistical value (plus won leads as "realized");
    in "invoices" mode paid invoice totals drive the bar instead."""
    s = await get_or_create_settings(db)
    today_date = date.today()
    if s.dream_start_date is None:
        # First visit starts the challenge.
        s.dream_start_date = today_date
        await db.flush()
    start = s.dream_start_date
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)

    ev_unit = dream_ev_per_contact(
        s.dream_avg_deal_value, s.dream_savings_rate_pct, s.dream_contacts_per_win
    )
    rate = Decimal(s.dream_savings_rate_pct) / Decimal(100)

    async def _activity_ev_since(since: datetime) -> tuple[dict, Decimal]:
        rows = (await db.execute(
            select(RainmakerActivity.type, func.count())
            .where(
                RainmakerActivity.status == RainmakerActivityStatus.done,
                RainmakerActivity.completed_at >= since,
            )
            .group_by(RainmakerActivity.type)
        )).all()
        counts = {t: int(c) for t, c in rows}
        return counts, dream_activities_ev(counts, ev_unit)

    async def _won_since(since: datetime) -> tuple[int, Decimal]:
        # Won leads since `since` — updated_at is the proxy for the win date.
        row = (await db.execute(
            select(func.count(), func.coalesce(func.sum(RainmakerLead.value_estimate), 0))
            .where(
                RainmakerLead.status == RainmakerLeadStatus.won,
                RainmakerLead.updated_at >= since,
            )
        )).one()
        return int(row[0]), Decimal(row[1] or 0)

    async def _paid_invoices_since(since: date) -> Decimal:
        total = (await db.execute(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.status == InvoiceStatus.bezahlt,
                Invoice.invoice_date >= since,
            )
        )).scalar_one()
        return Decimal(total or 0)

    counts, acts_ev = await _activity_ev_since(start_dt)
    won_count, won_value = await _won_since(start_dt)
    won_ev = (won_value * rate).quantize(Decimal("0.01"))
    invoices_paid = await _paid_invoices_since(start)
    invoices_ev = (invoices_paid * rate).quantize(Decimal("0.01"))

    if s.dream_mode == RainmakerDreamMode.invoices:
        saved_total = invoices_ev
    else:
        saved_total = (acts_ev + won_ev).quantize(Decimal("0.01"))

    price = Decimal(s.dream_goal_price)
    pct = float(min(saved_total / price, Decimal(1))) if price > 0 else 0.0

    # Today's earned value (clipped to the challenge start).
    today_dt = datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc)
    _tc, today_ev = await _activity_ev_since(max(today_dt, start_dt))

    # Pace: Ø €/day over the last 28 days (window clipped to the start date).
    window_start = max(start, today_date - timedelta(days=27))
    window_days = (today_date - window_start).days + 1
    window_dt = datetime.combine(window_start, datetime.min.time(), tzinfo=timezone.utc)
    if s.dream_mode == RainmakerDreamMode.invoices:
        window_total = (await _paid_invoices_since(window_start)) * rate
    else:
        _wc, window_acts_ev = await _activity_ev_since(window_dt)
        _wn, window_won_value = await _won_since(window_dt)
        window_total = window_acts_ev + window_won_value * rate
    pace_per_day = (window_total / window_days).quantize(Decimal("0.01"))

    return RainmakerDreamResponse(
        goal_key=s.dream_goal_key,
        goal_name=s.dream_goal_name or _DREAM_DEFAULT_NAME,
        goal_price=price,
        savings_rate_pct=s.dream_savings_rate_pct,
        avg_deal_value=s.dream_avg_deal_value,
        contacts_per_win=s.dream_contacts_per_win,
        start_date=start,
        mode=s.dream_mode,
        ev_per_contact=ev_unit,
        ev_weights={t.value: w for t, w in DREAM_EV_WEIGHTS.items()},
        counts_by_type=[RmTypeCount(type=t, count=c) for t, c in counts.items()],
        activities_ev=acts_ev,
        won_count=won_count,
        won_value=won_value,
        won_ev=won_ev,
        invoices_paid=invoices_paid,
        invoices_ev=invoices_ev,
        saved_total=saved_total,
        pct=pct,
        today_ev=today_ev,
        pace_per_day=pace_per_day,
        projected_date=dream_projected_date(price - saved_total, pace_per_day, today_date),
        days_active=(today_date - start).days + 1,
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
