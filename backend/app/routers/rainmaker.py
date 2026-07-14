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
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
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
    AiBudget,
    AiDiscoverRequest,
    AiDiscoverResponse,
    AiRunCost,
    AiUsageResponse,
    DiscoveredCandidate,
    DuplicateGroup,
    DuplicateMergeBatchRequest,
    DuplicateMergeBatchResult,
    DuplicateMergeFailure,
    DuplicateMergeRequest,
    DuplicateMergeResult,
    ImportSkipped,
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
from app.services.lead_dedup import (
    MATCH_EMAIL,
    MATCH_NAME,
    MATCH_WEBSITE,
    DedupIndex,
    norm_email,
    norm_name,
    norm_website,
)
from app.models.ai_lead_run import AiLeadRun
from app.services.ai_lead_agent import run_ai_discovery
from app.services.ai_pricing import ALLOWED_MODELS, DEFAULT_MODEL
from app.services.duplicate_finder import find_groups
from app.services.email_verifier import verify_email
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
    force: bool = Query(False, description="Duplikat-Warnung übergehen und trotzdem anlegen"),
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    # Duplikat-Warnung (kein hartes Blocken — bewusstes Anlegen via force=true).
    if not force:
        dup, reason = await find_duplicate_lead(
            db, email=data.email, website=data.website, contact_name=data.contact_name)
        if dup is not None:
            raise HTTPException(status_code=409, detail={
                "message": f"Ähnlicher Lead existiert bereits ({_REASON_LABEL.get(reason, reason)}: "
                           f"„{dup.company}“). Trotzdem anlegen?",
                "reason": reason,
                "existing_id": str(dup.id),
                "existing_company": dup.company,
            })
    lead = RainmakerLead(**data.model_dump())
    lead.email_status = await _email_status_for(data.email)
    if not await _safe_flush_lead(db, lead):
        # Race: ein paralleler Insert war schneller.
        raise HTTPException(status_code=409, detail={
            "message": "Ein identischer Lead wurde gerade parallel angelegt.",
            "reason": MATCH_WEBSITE,
        })
    await db.refresh(lead)
    return lead_response(lead)


@router.put("/leads/{lead_id}", response_model=RainmakerLeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    data: RainmakerLeadUpdate,
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    lead = await _get_lead_or_404(lead_id, db)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)
    # E-Mail geändert → Qualitätsurteil neu berechnen
    if "email" in update_data:
        lead.email_status = await _email_status_for(lead.email)
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


@router.post("/leads/verify-emails")
async def verify_all_emails(
    only_unchecked: bool = Query(True, description="Nur noch nicht geprüfte Leads"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Backfill/Sammelprüfung: berechnet das E-Mail-Urteil für alle Leads mit
    E-Mail (owner-scoped via Events), geteilter MX-Cache. Report als Zähler."""
    q = select(RainmakerLead).where(
        RainmakerLead.email.isnot(None), RainmakerLead.email != "")
    if only_unchecked:
        q = q.where(RainmakerLead.email_status.is_(None))
    leads = (await db.execute(q)).scalars().all()
    cache: dict = {}
    counts: dict[str, int] = {}
    for lead in leads:
        st = await _email_status_for(lead.email, cache)
        lead.email_status = st
        counts[st or "none"] = counts.get(st or "none", 0) + 1
    await db.flush()
    return {"checked": len(leads), "by_status": counts}


@router.post("/leads/{lead_id}/verify-email", response_model=RainmakerLeadResponse)
async def verify_lead_email(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RainmakerLeadResponse:
    """E-Mail eines einzelnen Leads (neu) prüfen und Urteil speichern."""
    lead = await _get_lead_or_404(lead_id, db)
    lead.email_status = await _email_status_for(lead.email)
    await db.flush()
    await db.refresh(lead)
    return lead_response(lead)


# --------------------------------------------------------------------------- #
#  LinkedIn-Import (offizieller Connections.csv-Datenexport — keine API)
# --------------------------------------------------------------------------- #
_LINKEDIN_IMPORT_MAX_BYTES = 10 * 1024 * 1024
_LINKEDIN_IMPORT_MAX_ROWS = 20_000


# Menschenlesbare Match-Gründe für den Import-Report.
_REASON_LABEL = {MATCH_EMAIL: "E-Mail", MATCH_WEBSITE: "Website", MATCH_NAME: "Name"}


async def _build_dedup_index(db: AsyncSession) -> tuple[DedupIndex, dict]:
    """DedupIndex + {id: lead} aller bestehenden Leads des Owners (owner-scoped
    via Tenancy-Events). Auto-Skip-Keys: E-Mail, Website, exakter Ansprechpartner-
    Name — NICHT der Firmenname (verschiedene Personen, gleicher Arbeitgeber)."""
    leads = (await db.execute(select(RainmakerLead))).scalars().all()
    idx = DedupIndex()
    by_id: dict = {}
    for lead in leads:
        idx.add(lead, email=lead.email, website=lead.website, name=lead.contact_name)
        by_id[str(lead.id)] = lead
    return idx, by_id


async def find_duplicate_lead(
    db: AsyncSession, *, email: str | None, website: str | None,
    contact_name: str | None,
) -> tuple[RainmakerLead | None, str | None]:
    """Einzel-Lookup (für die manuelle Anlage) über die generierten Dedup-Spalten
    (indexgestützt). Rückgabe: (Lead, Grund) oder (None, None)."""
    e, w, n = norm_email(email), norm_website(website), norm_name(contact_name)
    conds = []
    if e:
        conds.append(RainmakerLead.email_norm == e)
    if w:
        conds.append(RainmakerLead.website_norm == w)
    if n:
        conds.append(func.lower(func.btrim(RainmakerLead.contact_name)) == n)
    if not conds:
        return None, None
    lead = (await db.execute(select(RainmakerLead).where(or_(*conds)).limit(1))).scalar_one_or_none()
    if lead is None:
        return None, None
    if e and lead.email_norm == e:
        return lead, MATCH_EMAIL
    if w and lead.website_norm == w:
        return lead, MATCH_WEBSITE
    return lead, MATCH_NAME


async def _email_status_for(email: str | None, cache: dict | None = None) -> str | None:
    """E-Mail-Qualitätsurteil (SMTP-frei) für einen Lead — None ohne E-Mail.
    `cache` teilt MX-Ergebnisse über einen Import-Batch."""
    if not (email or "").strip():
        return None
    check = await verify_email(email, mx_cache=cache)
    return check.status.value


async def _safe_flush_lead(db: AsyncSession, lead: RainmakerLead) -> bool:
    """Fügt einen Lead in einem SAVEPOINT ein und fängt eine Unique-Verletzung
    (paralleler Import / Race gegen die partiellen Unique-Indizes) ab → False,
    ohne die ganze Transaktion zu zerstören. True bei Erfolg."""
    db.add(lead)
    try:
        async with db.begin_nested():
            await db.flush()
        return True
    except IntegrityError:
        return False


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

    idx, _ = await _build_dedup_index(db)
    out: list[LinkedInPreviewRow] = []

    def _is_duplicate(email: str | None, website: str | None, name: str) -> bool:
        lead, _reason = idx.match(email=email, website=website, name=name)
        # Datensatz in den Index aufnehmen → Batch-interne Duplikate erkennen.
        idx.add(object(), email=email, website=website, name=name)
        return lead is not None

    # Bestätigte Kontakte — mit Nachrichtenverlauf angereichert
    for r in rows:
        full_name = f"{r['first_name']} {r['last_name']}".strip()
        msg = messages.get(normalize_profile_url(r["url"]), None) if r["url"] else None
        out.append(LinkedInPreviewRow(
            **r,
            source="connection",
            status=RainmakerLeadStatus.in_conversation if msg else RainmakerLeadStatus.connected,
            message_count=msg["count"] if msg else 0,
            last_message_at=msg["last_date"] if msg else "",
            messages=msg["messages"] if msg else [],
            duplicate=_is_duplicate(r.get("email"), r["url"], full_name),
        ))

    # Offene ausgehende Kontaktanfragen (nicht in Connections → noch unbeantwortet)
    connection_urls = {normalize_profile_url(r["url"]) for r in rows if r["url"]}
    for inv in invitations:
        inv_url = normalize_profile_url(inv["url"])
        if inv_url and inv_url in connection_urls:
            continue  # inzwischen angenommen → ist als Connection drin
        parts = inv["name"].split(" ", 1)
        first, last = parts[0], (parts[1] if len(parts) > 1 else "")
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
            duplicate=_is_duplicate(None, inv["url"], inv["name"].strip()),
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

    # Lead-Lookup für Enrichment (owner-scoped via Tenancy-Events).
    # DedupIndex matcht auf E-Mail → Website/Profil-URL → exakten Namen.
    idx, _ = await _build_dedup_index(db)

    _status_rank = {
        RainmakerLeadStatus.new: 0,
        RainmakerLeadStatus.contacted: 1,
        RainmakerLeadStatus.connected: 2,
        RainmakerLeadStatus.in_conversation: 3,
    }

    created = skipped = enriched = activities_created = 0
    skipped_rows: list[ImportSkipped] = []
    mx_cache: dict = {}
    for row in data.rows:
        fields = row_to_lead_fields(row.model_dump())
        full_name = f"{row.first_name} {row.last_name}".strip()
        existing_lead, reason = idx.match(email=fields.get("email"), website=row.url, name=full_name)
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
                existing_lead.email_status = await _email_status_for(fields["email"], mx_cache)
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
                skipped_rows.append(ImportSkipped(
                    name=full_name or existing_lead.company, reason=reason or MATCH_WEBSITE))
            continue
        if row.source == "invitation":
            note = "LinkedIn-Kontaktanfrage gesendet"
            if row.invited_at:
                note += f" am {row.invited_at}"
            note += " (noch nicht angenommen)"
            fields["notes"] = note
        fields["status"] = row.status
        lead = RainmakerLead(**fields)
        lead.email_status = await _email_status_for(fields.get("email"), mx_cache)
        if not await _safe_flush_lead(db, lead):
            # Race gegen einen parallelen Import (partieller Unique-Index) → Skip
            skipped += 1
            skipped_rows.append(ImportSkipped(name=full_name, reason=MATCH_WEBSITE))
            continue

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

        # Neu angelegten Lead in den Index — Mehrfachzeilen derselben Person
        # innerhalb eines Batches werden so angereichert/übersprungen statt dupliziert
        idx.add(lead, email=fields.get("email"), website=row.url, name=full_name)
        created += 1
    await db.flush()
    return LinkedInImportResult(
        created=created,
        skipped_duplicates=skipped,
        enriched=enriched,
        activities_created=activities_created,
        skipped_rows=skipped_rows,
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
@router.post("/discover/preview", response_model=list[DiscoveredCandidate])
async def discover_preview(
    data: LeadDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
) -> list[DiscoveredCandidate]:
    """Sucht Firmen nach Branche + Ort und markiert Duplikate (bereits als Lead
    vorhanden, per E-Mail oder Website; owner-scoped). Legt nichts an. Der
    Firmenname ist bewusst KEIN Auto-Key (verschiedene Betriebe/Personen)."""
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
                candidates, api_calls = await discover_google(data.category, data.location, data.limit, places_key, client)
                # Eigenen Nutzungszähler um die echten API-Calls (Text-Suche + Details) hochzählen.
                if app_row is not None:
                    app_row.google_places_period, app_row.google_places_calls = bump(
                        app_row.google_places_period, app_row.google_places_calls, increment=api_calls)
            else:
                candidates = await discover_osm(data.category, data.location, data.limit, client)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Suche fehlgeschlagen: {exc}")

    idx, _ = await _build_dedup_index(db)
    out: list[DiscoveredCandidate] = []
    for c in candidates:
        lead, reason = idx.match(email=c.get("email"), website=c.get("website"))
        # Batch-intern: Kandidat in den Index aufnehmen (mehrere Kombinationen
        # können dieselbe Firma liefern).
        idx.add(object(), email=c.get("email"), website=c.get("website"))
        out.append(DiscoveredCandidate(
            **c, duplicate=lead is not None,
            duplicate_reason=reason if lead is not None else None,
        ))
    return out


@router.post("/discover/import", response_model=LeadDiscoveryResult)
async def discover_import(
    data: LeadDiscoveryImportRequest,
    db: AsyncSession = Depends(get_db),
) -> LeadDiscoveryResult:
    """Legt die ausgewählten Kandidaten als Leads an (Status 'new'), mit Quelle
    und owner-scoped Dedup-Wiederprüfung (E-Mail/Website, Doppel-Submit- und
    Race-sicher via partielle Unique-Indizes)."""
    if len(data.rows) > 5000:
        raise HTTPException(status_code=413, detail="Zu viele Kandidaten (max. 5000)")
    idx, _ = await _build_dedup_index(db)
    created = skipped = 0
    skipped_rows: list[ImportSkipped] = []
    mx_cache: dict = {}
    tags = ["discovery"]
    if data.segment:
        tags.append(data.segment)
    for c in data.rows:
        lead, reason = idx.match(email=c.email, website=c.website)
        if lead is not None:
            skipped += 1
            skipped_rows.append(ImportSkipped(name=c.name or "?", reason=reason or MATCH_WEBSITE))
            continue
        new_lead = RainmakerLead(
            company=(c.name or "").strip()[:255] or "Unbenannt",
            website=(c.website or "").strip()[:500] or None,
            email=(c.email or "").strip()[:255] or None,
            phone=(c.phone or "").strip()[:50] or None,
            address=(c.address or "").strip() or None,
            source=c.source,
            status=RainmakerLeadStatus.new,
            tags=tags,
            notes=f"Automatisch gefunden ({c.source})" + (f" · Ref {c.source_ref}" if c.source_ref else ""),
        )
        new_lead.email_status = await _email_status_for(c.email, mx_cache)
        if not await _safe_flush_lead(db, new_lead):
            skipped += 1
            skipped_rows.append(ImportSkipped(name=c.name or "?", reason=MATCH_WEBSITE))
            continue
        idx.add(new_lead, email=c.email, website=c.website)
        created += 1
    await db.flush()
    return LeadDiscoveryResult(
        created=created, skipped_duplicates=skipped, skipped_rows=skipped_rows)


# --------------------------------------------------------------------------- #
#  KI-Lead-Suche (Anthropic) — Brief → verifizierte, gerankte Kandidaten
# --------------------------------------------------------------------------- #
def _budget_status(spent_eur: float, budget_eur: float) -> AiBudget:
    return AiBudget(
        budget_eur=round(budget_eur, 2), spent_eur=round(spent_eur, 4),
        remaining_eur=round(max(0.0, budget_eur - spent_eur), 4),
        warn=budget_eur > 0 and spent_eur >= 0.8 * budget_eur,
    )


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _ai_month_spent_eur(db: AsyncSession) -> float:
    """EUR-Verbrauch der KI-Läufe im laufenden Monat (owner-scoped via Events)."""
    total = (await db.execute(
        select(func.coalesce(func.sum(AiLeadRun.cost_eur), 0))
        .where(AiLeadRun.created_at >= _month_start())
    )).scalar_one()
    return float(total or 0)


@router.post("/discover/ai/preview", response_model=AiDiscoverResponse)
async def ai_discover_preview(
    data: AiDiscoverRequest,
    db: AsyncSession = Depends(get_db),
) -> AiDiscoverResponse:
    """Freitext-Brief → KI-recherchierte, verifizierte (Website live + E-Mail-MX)
    und nach Fit gerankte Kandidaten. Legt nichts an. Protokolliert Kosten und
    setzt das Monatsbudget hart durch."""
    import httpx

    from app.models.app_settings import AppSettings
    from app.services.exchange_service import get_usd_eur_rate

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503,
                            detail="KI-Lead-Suche ist nicht konfiguriert (ANTHROPIC_API_KEY fehlt in der .env).")

    app_row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    model = data.model or (app_row.ai_model if app_row else DEFAULT_MODEL)
    if model not in ALLOWED_MODELS:
        model = DEFAULT_MODEL
    budget_eur = float(app_row.ai_monthly_budget_eur) if app_row else 20.0

    spent = await _ai_month_spent_eur(db)
    if budget_eur > 0 and spent >= budget_eur:
        raise HTTPException(status_code=402, detail=(
            f"KI-Monatsbudget erreicht ({spent:.2f} € / {budget_eur:.2f} €). "
            "Budget in den Einstellungen erhöhen, um weitere Läufe zu starten."))

    try:
        async with httpx.AsyncClient(timeout=40, headers={"User-Agent": "celox-ops-rainmaker/1.0"}) as client:
            result = await run_ai_discovery(
                brief=data.brief, model=model, use_web_search=data.use_web_search,
                api_key=settings.ANTHROPIC_API_KEY, http_client=client)
    except Exception as exc:  # noqa: BLE001
        db.add(AiLeadRun(brief=data.brief[:2000], model=model,
                         used_web_search=data.use_web_search, status="failed",
                         error=str(exc)[:1000]))
        await db.flush()
        raise HTTPException(status_code=502, detail=f"KI-Lauf fehlgeschlagen: {exc}")

    from app.services.ai_pricing import get_pricing

    usage = result.usage
    cost_usd = usage.cost_with(await get_pricing(model))   # dynamische Preise (12-h-Cache)
    cost_eur = round(cost_usd * await get_usd_eur_rate(), 4)

    db.add(AiLeadRun(
        brief=data.brief[:2000], model=model, used_web_search=data.use_web_search,
        cost_usd=cost_usd, cost_eur=cost_eur,
        candidates_found=len(result.candidates), status="ok", **usage.as_dict()))
    await db.flush()

    # Duplikat-Markierung gegen den Bestand (wie bei der normalen Discovery).
    idx, _ = await _build_dedup_index(db)
    out: list[DiscoveredCandidate] = []
    for c in result.candidates:
        lead, reason = idx.match(email=c.get("email"), website=c.get("website"))
        idx.add(object(), email=c.get("email"), website=c.get("website"))
        out.append(DiscoveredCandidate(
            name=c.get("name") or "?", website=c.get("website"), email=c.get("email"),
            phone=c.get("phone"), address=c.get("address"), source="KI-Recherche",
            source_ref=c.get("source_ref"), email_status=c.get("email_status"),
            fit_reason=c.get("fit_reason"),
            duplicate=lead is not None, duplicate_reason=reason if lead is not None else None))

    return AiDiscoverResponse(
        candidates=out,
        run=AiRunCost(model=model, cost_usd=round(cost_usd, 6), cost_eur=cost_eur, **usage.as_dict()),
        budget=_budget_status(spent + cost_eur, budget_eur),
        notes=result.notes)


@router.get("/ai/usage", response_model=AiUsageResponse)
async def ai_usage(db: AsyncSession = Depends(get_db)) -> AiUsageResponse:
    """Kosten-Übersicht der KI-Lead-Suche: Monatsverbrauch, Budget, letzte Läufe."""
    from app.models.app_settings import AppSettings
    from app.services.ai_pricing import get_pricing, pricing_source

    app_row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    budget_eur = float(app_row.ai_monthly_budget_eur) if app_row else 20.0
    model = app_row.ai_model if app_row else DEFAULT_MODEL
    await get_pricing(model)              # Preise (dynamisch) laden/cachen → Quelle bekannt

    month_rows = list((await db.execute(
        select(AiLeadRun).where(AiLeadRun.created_at >= _month_start()))).scalars().all())
    spent_eur = sum(float(r.cost_eur) for r in month_rows)
    spent_usd = sum(float(r.cost_usd) for r in month_rows)
    runs = len(month_rows)
    recent = list((await db.execute(
        select(AiLeadRun).order_by(AiLeadRun.created_at.desc()).limit(10))).scalars().all())

    return AiUsageResponse(
        budget=_budget_status(spent_eur, budget_eur),
        runs_this_month=runs, spent_usd=round(spent_usd, 4),
        avg_cost_eur=round(spent_eur / runs, 4) if runs else 0.0,
        configured=bool(settings.ANTHROPIC_API_KEY), model=model,
        pricing_source=pricing_source(), recent=recent)


# --------------------------------------------------------------------------- #
#  Duplikat-Bereinigung (find + merge)
# --------------------------------------------------------------------------- #
@router.get("/duplicates", response_model=list[DuplicateGroup])
async def list_duplicates(db: AsyncSession = Depends(get_db)) -> list[DuplicateGroup]:
    """Kandidaten-Duplikatgruppen des Owners (nach Konfidenz sortiert). Da E-Mail
    und Website bereits pro Owner unique sind, greift dies über den Firmennamen
    (exakt + fuzzy) und gewichtet nach Typ (dieselbe Person / Firma doppelt /
    evtl. Kollegen). Legt oder löscht nichts."""
    leads = (await db.execute(select(RainmakerLead))).scalars().all()
    counts = dict((await db.execute(
        select(RainmakerActivity.lead_id, func.count())
        .group_by(RainmakerActivity.lead_id)
    )).all())
    dicts = [{
        "id": le.id, "company": le.company, "contact_name": le.contact_name,
        "role": le.role, "email": le.email, "website": le.website, "phone": le.phone,
        "source": le.source, "status": le.status, "created_at": le.created_at,
        "activity_count": counts.get(le.id, 0),
    } for le in leads]
    return [DuplicateGroup(**g) for g in find_groups(dicts)]


def merge_overlap_indices(merges: list) -> set:
    """Indizes der Merges, deren Leads (Keeper oder Duplikat) in mehr als einer
    Gruppe vorkommen — die dürfen im Batch nicht ausgeführt werden. Rein/testbar
    (jedes Element braucht `.keeper_id` + `.duplicate_ids`)."""
    lead_to_group: dict = {}
    overlap: set = set()
    for i, m in enumerate(merges):
        for lid in {m.keeper_id, *m.duplicate_ids}:
            if lid in lead_to_group and lead_to_group[lid] != i:
                overlap.add(i)
                overlap.add(lead_to_group[lid])
            lead_to_group[lid] = i
    return overlap


async def _merge_lead_group(db: AsyncSession, current_user, keeper_id: uuid.UUID,
                            duplicate_ids: list) -> tuple[RainmakerLead, int, int]:
    """Führt `duplicate_ids` in den Keeper zusammen (Aktivitäten umhängen, leere
    Keeper-Felder + Tags übernehmen, Duplikate löschen). Owner-scoped validiert;
    `ValueError` bei Validierungsfehler. Ruft KEIN flush/refresh (macht der
    Aufrufer — beim Batch im SAVEPOINT). Rückgabe: (keeper, moved, deleted)."""
    dup_ids = list(dict.fromkeys(duplicate_ids))
    if not dup_ids:
        raise ValueError("Keine Duplikate angegeben.")
    if keeper_id in dup_ids:
        raise ValueError("Der Behalten-Lead darf nicht in den Duplikaten stehen.")

    keeper = (await db.execute(
        select(RainmakerLead).where(RainmakerLead.id == keeper_id))).scalar_one_or_none()
    if keeper is None or keeper.owner_id != current_user.id:
        raise ValueError("Behalten-Lead nicht gefunden.")
    dups = list((await db.execute(
        select(RainmakerLead).where(RainmakerLead.id.in_(dup_ids)))).scalars().all())
    if len(dups) != len(dup_ids) or any(d.owner_id != current_user.id for d in dups):
        raise ValueError("Mindestens ein Duplikat wurde nicht gefunden.")

    fill: dict = {}
    tags = set(keeper.tags or [])
    for d in dups:
        for f in ("contact_name", "role", "email", "website", "phone", "address"):
            if not getattr(keeper, f) and f not in fill and getattr(d, f):
                fill[f] = getattr(d, f)
        if keeper.value_estimate is None and "value_estimate" not in fill and d.value_estimate is not None:
            fill["value_estimate"] = d.value_estimate
        tags.update(d.tags or [])

    for d in dups:
        db.expunge(d)   # kein ORM-Cascade auf die gleich umgehängten Aktivitäten

    # Aktivitäten auf den Keeper umhängen (Historie retten); owner_id explizit (Bulk-
    # DML wird von den Tenancy-Events nicht gescopet).
    moved = (await db.execute(
        sa_update(RainmakerActivity).where(
            RainmakerActivity.lead_id.in_(dup_ids),
            RainmakerActivity.owner_id == current_user.id,
        ).values(lead_id=keeper.id).execution_options(synchronize_session=False)
    )).rowcount or 0
    # Duplikate löschen (Unique-Keys werden frei), dann leere Keeper-Felder + Tags.
    await db.execute(
        sa_delete(RainmakerLead).where(
            RainmakerLead.id.in_(dup_ids),
            RainmakerLead.owner_id == current_user.id,
        ).execution_options(synchronize_session=False))
    for f, v in fill.items():
        setattr(keeper, f, v)
    if tags != set(keeper.tags or []):
        keeper.tags = sorted(tags)
    return keeper, moved, len(dups)


@router.post("/duplicates/merge", response_model=DuplicateMergeResult)
async def merge_duplicates(
    data: DuplicateMergeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DuplicateMergeResult:
    """Führt die angegebenen Duplikate in den Keeper zusammen (Aktivitäten bleiben,
    leere Felder/Tags übernommen, Duplikate gelöscht). Owner-scoped, ohne Undo."""
    try:
        keeper, moved, deleted = await _merge_lead_group(
            db, current_user, data.keeper_id, data.duplicate_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.flush()
    await db.refresh(keeper)
    return DuplicateMergeResult(
        keeper=lead_response(keeper), merged_leads=deleted, moved_activities=moved)


@router.post("/duplicates/merge-batch", response_model=DuplicateMergeBatchResult)
async def merge_duplicates_batch(
    data: DuplicateMergeBatchRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DuplicateMergeBatchResult:
    """Mehrere Gruppen in einem Rutsch zusammenführen. **Kollisionsprüfung vorab**
    (kein Lead darf in mehreren Merges vorkommen) + **jeder Merge isoliert im
    SAVEPOINT** → ein Fehler stoppt die anderen nicht, wird aber berichtet."""
    if not data.merges:
        raise HTTPException(status_code=400, detail="Keine Gruppen angegeben.")
    if len(data.merges) > 500:
        raise HTTPException(status_code=413, detail="Zu viele Gruppen (max. 500).")

    # Firmennamen der Keeper für verständliche Fehlermeldungen.
    keeper_ids = [m.keeper_id for m in data.merges]
    names = dict((await db.execute(
        select(RainmakerLead.id, RainmakerLead.company)
        .where(RainmakerLead.id.in_(keeper_ids)))).all())

    # Vorab-Overlap: ein Lead (Keeper oder Duplikat) darf nur in EINER Gruppe stehen.
    overlap = merge_overlap_indices(data.merges)

    merged_groups = deleted_total = moved_total = 0
    failed: list[DuplicateMergeFailure] = []
    for i, m in enumerate(data.merges):
        company = names.get(m.keeper_id) or "?"
        if i in overlap:
            failed.append(DuplicateMergeFailure(
                company=company, reason="Lead kommt in mehreren Gruppen vor — übersprungen"))
            continue
        try:
            async with db.begin_nested():
                _keeper, moved, deleted = await _merge_lead_group(
                    db, current_user, m.keeper_id, m.duplicate_ids)
                await db.flush()
            merged_groups += 1
            deleted_total += deleted
            moved_total += moved
        except (ValueError, IntegrityError) as exc:
            failed.append(DuplicateMergeFailure(company=company, reason=str(exc)[:150]))

    await db.flush()
    return DuplicateMergeBatchResult(
        merged_groups=merged_groups, deleted_leads=deleted_total,
        moved_activities=moved_total, failed=failed)


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
