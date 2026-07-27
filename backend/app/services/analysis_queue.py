"""In-Process-Worker für die automatische Website-Analyse nach dem Lead-Import.

Aufbau wie der bestehende stündliche Cron: eine asyncio-Task im FastAPI-Lifespan,
die eigene DB-Sessions öffnet. Kein Celery/Redis — die Last ist klein (ein HTTP-
Abruf + reine Auswertung pro Lead) und eine zweite Infrastruktur wäre für diesen
Zweck nicht zu rechtfertigen.

**Mandanten-Invariante:** der Worker läuft ohne gesetzten `current_owner_id`
(→ Selects sind global, so findet er die Jobs aller Nutzer) und setzt den
ContextVar **pro Job** auf `job.owner_id`, bevor er Lead und Analyse anfasst.

Nur die **schnelle** technische Analyse (kein PageSpeed, keine KI) — der
Auto-Lauf darf niemals Kosten verursachen. Tiefenanalyse bleibt ein bewusster
Klick im Lead-Detail.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select

from app.database import async_session_factory
from app.models.lead_analysis_job import DONE, ERROR, QUEUED, RUNNING, LeadAnalysisJob
from app.models.rainmaker_lead import RainmakerLead
from app.tenancy import current_owner_id

logger = logging.getLogger(__name__)

# Wie viele Analysen gleichzeitig laufen. Bewusst klein: der VPS teilt die CPU
# mit allem anderen, und fremde Websites sollen nicht geflutet werden.
CONCURRENCY = 2
# Ruhepause, wenn die Queue leer ist.
IDLE_SECONDS = 20
# Ein zweiter Versuch reicht — hängt eine Seite dauerhaft, hilft Wiederholen nicht.
MAX_ATTEMPTS = 2
# Sicherheitsnetz gegen hängengebliebene Jobs (Neustart mitten im Lauf).
STALE_MINUTES = 15
# Wie oft nach hängenden Jobs gesucht wird. **Nicht nur beim Start:** wird beim
# Deploy ein Job mitten im Lauf abgebrochen und ist beim Neustart jünger als
# STALE_MINUTES, blieb er sonst für immer auf „running" — die Pipeline-Pille
# drehte dann endlos.
STALE_CHECK_EVERY = 20
# Obergrenze für den Nachzieh-Lauf („alle ohne Analyse einreihen").
ENQUEUE_MISSING_CAP = 500


async def enqueue_leads(db, lead_ids: list) -> int:
    """Leads für die Auto-Analyse einreihen (owner-scoped über die Session-Events).

    Überspringt Leads, für die bereits ein offener Job (queued/running) existiert
    — ein erneuter Import derselben Firma erzeugt so keine Doppel-Analyse.
    """
    ids = [i for i in lead_ids if i is not None]
    if not ids:
        return 0
    open_rows = (await db.execute(
        select(LeadAnalysisJob.lead_id).where(
            LeadAnalysisJob.lead_id.in_(ids),
            LeadAnalysisJob.status.in_([QUEUED, RUNNING]),
        )
    )).scalars().all()
    pending = set(open_rows)
    added = 0
    for lead_id in ids:
        if lead_id in pending:
            continue
        db.add(LeadAnalysisJob(lead_id=lead_id, status=QUEUED))
        pending.add(lead_id)
        added += 1
    if added:
        await db.flush()
    return added


async def auto_analyze_enabled(db) -> bool:
    """Workspace-Schalter (Default an). Fehlt die Zeile, gilt „an"."""
    from app.models.app_settings import AppSettings

    row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    return True if row is None else bool(row.auto_analyze_websites)


async def enqueue_after_import(db, lead_ids: list) -> int:
    """Einreihen, sofern der Workspace-Schalter an ist (sonst 0)."""
    if not lead_ids or not await auto_analyze_enabled(db):
        return 0
    return await enqueue_leads(db, lead_ids)


async def enqueue_company_websites(db, lead_ids: list) -> int:
    """Wie `enqueue_after_import`, filtert aber vorher Social-/Profil-URLs aus.

    Genutzt vom Lead-Anlegen: dort kann als „Website" auch ein LinkedIn-Profil
    stehen (so kommen LinkedIn-Kontakte in den Bestand).
    """
    if not lead_ids or not await auto_analyze_enabled(db):
        return 0
    rows = (await db.execute(
        select(RainmakerLead.id, RainmakerLead.website)
        .where(RainmakerLead.id.in_(lead_ids))
    )).all()
    return await enqueue_leads(db, [i for i, w in rows if is_company_website(w)])


async def queue_stats(db) -> dict:
    """Zählerstand für die UI (owner-scoped): offen/laufend/fertig/Fehler."""
    rows = (await db.execute(
        select(LeadAnalysisJob.status, func.count()).group_by(LeadAnalysisJob.status)
    )).all()
    counts = {status: int(n) for status, n in rows}
    return {
        "queued": counts.get(QUEUED, 0),
        "running": counts.get(RUNNING, 0),
        "done": counts.get(DONE, 0),
        "error": counts.get(ERROR, 0),
        "pending": counts.get(QUEUED, 0) + counts.get(RUNNING, 0),
    }


# Hosts, deren „Website" kein Firmenauftritt ist. LinkedIn-Importe tragen im
# website-Feld das PROFIL — analysieren wäre sinnlos (Bot-Sperre, kein
# Firmenauftritt) und würde Tausende Anfragen an einen Host schicken. Der
# Auto-Import überspringt sie schon; hier gilt dieselbe Regel an einer Stelle.
NON_COMPANY_HOSTS = ("linkedin.com", "xing.com", "facebook.com", "instagram.com")


def is_company_website(url: str | None) -> bool:
    """False für Social-/Profil-URLs — die sind keine Firmenwebsite. Rein."""
    text = (url or "").strip().lower()
    if not text:
        return False
    return not any(host in text for host in NON_COMPANY_HOSTS)


async def leads_needing_analysis(db, cap: int = ENQUEUE_MISSING_CAP) -> list:
    """IDs der Leads mit echter Firmen-Website, aber ohne Analyse (owner-scoped)."""
    rows = (await db.execute(
        select(RainmakerLead.id, RainmakerLead.website)
        .where(RainmakerLead.website.isnot(None), RainmakerLead.website != "",
               RainmakerLead.web_analyzed_at.is_(None))
        .order_by(RainmakerLead.created_at.desc())
        .limit(cap)
    )).all()
    return [lead_id for lead_id, website in rows if is_company_website(website)]


# --------------------------------------------------------------------------- #
#  Worker
# --------------------------------------------------------------------------- #
async def _reset_stale_jobs(db) -> int:
    """Jobs, die beim letzten Neustart mitten im Lauf waren, zurück auf queued."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)
    rows = (await db.execute(
        select(LeadAnalysisJob).where(
            LeadAnalysisJob.status == RUNNING,
            or_(LeadAnalysisJob.started_at.is_(None), LeadAnalysisJob.started_at < cutoff),
        )
    )).scalars().all()
    for job in rows:
        job.status = QUEUED
        job.started_at = None
    if rows:
        await db.flush()
    return len(rows)


async def _claim_jobs(db, limit: int) -> list[LeadAnalysisJob]:
    """Nächste Jobs übernehmen (global — der Worker hat keinen Owner-Kontext).

    `with_for_update(skip_locked=True)` macht das Übernehmen auch dann sicher,
    wenn irgendwann mehrere Backend-Container laufen.
    """
    jobs = (await db.execute(
        select(LeadAnalysisJob)
        .where(LeadAnalysisJob.status == QUEUED)
        .order_by(LeadAnalysisJob.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )).scalars().all()
    now = datetime.now(timezone.utc)
    for job in jobs:
        job.status = RUNNING
        job.started_at = now
        job.attempts = (job.attempts or 0) + 1
    if jobs:
        await db.commit()
    return list(jobs)


async def _run_job(job_id, owner_id, lead_id) -> None:
    """Eine Analyse in eigener Session + eigenem Owner-Kontext ausführen."""
    from app.services.website_analysis import fetch_and_analyze
    from app.services.website_analysis_store import persist_analysis

    async with async_session_factory() as db:
        token = current_owner_id.set(owner_id)
        try:
            job = await db.get(LeadAnalysisJob, job_id)
            lead = await db.get(RainmakerLead, lead_id)
            if job is None:
                return
            if owner_id is None:
                # Ein Job ohne Owner darf NICHT laufen: `current_owner_id` wäre
                # None, die Analyse würde ungescopet geschrieben und läge dann
                # mit owner_id NULL in der DB — der Lead zeigte einen Score,
                # das Detail-Dashboard (owner-scoped) fände aber keine Analyse.
                # Das kann nur durch fehlerhaftes Einreihen entstehen, also hier
                # sichtbar abweisen statt stumm unsichtbare Daten erzeugen.
                job.status = ERROR
                job.error = "Job ohne owner_id — nicht ausgeführt (fehlerhaft eingereiht)"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                logger.warning("Analyse-Worker: Job %s ohne owner_id abgewiesen", job_id)
                return
            if lead is None or not (lead.website or "").strip():
                job.status = ERROR
                job.error = "Lead hat keine Website (mehr)"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                return
            try:
                result = await fetch_and_analyze(lead.website)
                await persist_analysis(db, lead, result)
                job.status = DONE
                job.error = None
            except Exception as exc:  # noqa: BLE001 — Fehler gehört an den Job
                logger.warning("Auto-Analyse fehlgeschlagen (%s): %s", lead_id, exc)
                job.status = QUEUED if (job.attempts or 0) < MAX_ATTEMPTS else ERROR
                job.error = str(exc)[:500]
                if job.status == QUEUED:
                    job.started_at = None
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Auto-Analyse: Job %s konnte nicht abgeschlossen werden", job_id)
        finally:
            current_owner_id.reset(token)


async def run_analysis_worker() -> None:
    """Endlosschleife: Jobs übernehmen und mit begrenzter Parallelität abarbeiten."""
    logger.info("Website-Analyse-Worker gestartet (Parallelität: %d)", CONCURRENCY)
    tick = 0
    while True:
        try:
            async with async_session_factory() as db:
                # Beim Start (tick 0) und danach regelmäßig — ein Job, der beim
                # Deploy abgebrochen wurde, heilt so von selbst.
                if tick % STALE_CHECK_EVERY == 0:
                    reset = await _reset_stale_jobs(db)
                    if reset:
                        await db.commit()
                        logger.info("Analyse-Worker: %d hängende Jobs zurückgesetzt", reset)
                tick += 1
                jobs = await _claim_jobs(db, CONCURRENCY)
                claimed = [(j.id, j.owner_id, j.lead_id) for j in jobs]
            if not claimed:
                await asyncio.sleep(IDLE_SECONDS)
                continue
            await asyncio.gather(*[_run_job(*c) for c in claimed])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Analyse-Worker: unerwarteter Fehler")
            await asyncio.sleep(IDLE_SECONDS)
