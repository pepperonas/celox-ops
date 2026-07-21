import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import async_session_factory, engine
from app.models.customer import Base, Customer
from app.models.order import Order
from app.models.contract import Contract
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.time_entry import TimeEntry
from app.models.expense import Expense
from app.models.activity import Activity
from app.models.attachment import Attachment
from app.models.email_template import EmailTemplate
from app.models.pagespeed_result import PagespeedResult
from app.models.compliance_record import ComplianceRecord
from app.models.rainmaker_lead import RainmakerLead
from app.models.rainmaker_activity import RainmakerActivity
from app.models.rainmaker_goal import RainmakerGoal
from app.models.rainmaker_template import RainmakerTemplate
from app.models.rainmaker_settings import RainmakerSettings
from app.models.rainmaker_streak import RainmakerStreak
from app.models.app_settings import AppSettings
from app.models.ai_lead_run import AiLeadRun
from app.models.outreach_template import OutreachTemplate
from app.models.todo import Todo
import app.models.audit_log  # noqa: F401 — register for create_all (global, not owned)
import app.models.document_template  # noqa: F401 — register for create_all (global, not owned)
import app.models.user  # noqa: F401 — register for create_all (global, not owned)
from app.tenancy import install_tenancy_events, set_owned_models
from app.middleware.audit import AuditMiddleware
from app.services.cron_service import check_overdue_invoices

# Multi-tenant isolation: every owned entity is auto-scoped to the current user.
set_owned_models([
    Customer, Order, Contract, Invoice, Lead, TimeEntry, Expense, Activity, Attachment,
    EmailTemplate, PagespeedResult, ComplianceRecord, RainmakerLead, RainmakerActivity,
    RainmakerGoal, RainmakerTemplate, RainmakerSettings, RainmakerStreak, AppSettings,
    AiLeadRun, OutreachTemplate, Todo,
])
install_tenancy_events()

logger = logging.getLogger(__name__)

# Initialize Sentry if DSN configured
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )


async def run_cron() -> None:
    """Background cron: checks overdue invoices every hour."""
    while True:
        await asyncio.sleep(3600)
        try:
            async with async_session_factory() as db:
                try:
                    count = await check_overdue_invoices(db)
                    await db.commit()
                    if count > 0:
                        from app.routers.dashboard import invalidate_stats_cache
                        invalidate_stats_cache()
                        logger.info("Cron: %d Rechnungen als überfällig markiert", count)
                except Exception:
                    await db.rollback()
                    logger.exception("Cron: Fehler bei Überprüfung überfälliger Rechnungen")

                # Per-user cron tasks (multi-tenant): rainmaker reminder + auto-recurring invoices.
                try:
                    from sqlalchemy import select as _sel

                    from app.models.user import User as _User
                    from app.routers.dashboard import invalidate_stats_cache
                    from app.services.invoice_service import generate_due_recurring
                    from app.services.rainmaker_service import check_rainmaker_reminder
                    from app.tenancy import current_owner_id as _owner

                    active_users = (
                        await db.execute(_sel(_User).where(_User.is_active.is_(True)))
                    ).scalars().all()
                    for u in active_users:
                        # Token-Reset im finally — ein geleakter Owner würde den
                        # globalen Überfällig-Check des nächsten Ticks still scopen.
                        _owner_token = _owner.set(u.id)  # scope this user's owned data
                        try:
                            try:
                                await check_rainmaker_reminder(db, u)
                                await db.commit()
                            except Exception:
                                await db.rollback()
                                logger.exception("Cron: Rainmaker-Reminder für %s fehlgeschlagen", u.username)
                            try:
                                created = await generate_due_recurring(db)
                                if created:
                                    await db.commit()
                                    invalidate_stats_cache()
                                    logger.info("Cron: %d wiederkehrende Rechnung(en) für %s erstellt", len(created), u.username)
                            except Exception:
                                await db.rollback()
                                logger.exception("Cron: Recurring-Rechnungen für %s fehlgeschlagen", u.username)
                        finally:
                            _owner.reset(_owner_token)
                except Exception:
                    await db.rollback()
                    logger.exception("Cron: Per-Nutzer-Tasks fehlgeschlagen")
        except Exception:
            logger.exception("Cron: Unerwarteter Fehler")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Validate critical secrets
    if settings.JWT_SECRET == "change-me-in-production" or len(settings.JWT_SECRET) < 32:
        raise RuntimeError(
            "JWT_SECRET ist nicht oder unsicher konfiguriert. "
            "Setze einen mindestens 32 Zeichen langen, zufälligen Wert in .env."
        )
    if not settings.CORS_ORIGINS.strip():
        logger.warning(
            "CORS_ORIGINS leer — alle Cross-Origin-Requests werden blockiert. "
            "Setze CORS_ORIGINS=https://deine-domain.de in .env."
        )

    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Bootstrap: turn the .env admin into a real DB user on first start, so the
    # existing single-user login keeps working unchanged once auth is DB-backed.
    from sqlalchemy import select as _select

    from app.models.user import User, UserRole

    import secrets as _secrets

    async with async_session_factory() as session:
        has_user = (await session.execute(_select(User).limit(1))).scalar_one_or_none()
        if has_user is None and settings.ADMIN_PASSWORD_HASH:
            session.add(
                User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=settings.ADMIN_PASSWORD_HASH,
                    role=UserRole.admin,
                    is_active=True,
                    totp_secret=(settings.TOTP_SECRET or None),
                    # Reuse the legacy global iCal token for the admin so an existing
                    # calendar subscription keeps working (now scoped to the admin).
                    ical_token=(settings.ICAL_TOKEN or _secrets.token_urlsafe(24)),
                )
            )
            await session.commit()
            logger.info("Bootstrap: Admin-User '%s' angelegt", settings.ADMIN_USERNAME)

        # Backfill iCal tokens for any user missing one (admin keeps the legacy token).
        missing = (await session.execute(_select(User).where(User.ical_token.is_(None)))).scalars().all()
        for u in missing:
            if u.role == UserRole.admin and settings.ICAL_TOKEN:
                u.ical_token = settings.ICAL_TOKEN
            else:
                u.ical_token = _secrets.token_urlsafe(24)
        if missing:
            await session.commit()
            logger.info("Bootstrap: iCal-Token für %d Nutzer nachgezogen", len(missing))

    # Start background cron task
    cron_task = asyncio.create_task(run_cron())
    logger.info("Background-Cron gestartet (Intervall: 1h)")

    yield

    # Cleanup on shutdown
    cron_task.cancel()
    try:
        await cron_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Celox Ops",
    description="Business management backend for celox.io",
    version="1.0.0",
    lifespan=lifespan,
)

_origins_raw = (settings.CORS_ORIGINS or "").strip()
_allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()] if _origins_raw else []

app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Wire up the rate limiter (login endpoint is decorated)
from app.auth import limiter  # noqa: E402
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Zu viele Anfragen — bitte warten. ({exc.detail})"},
    )

# Import routers after app creation to avoid circular imports
from app.auth import router as auth_router  # noqa: E402
from app.routers.customers import router as customers_router  # noqa: E402
from app.routers.orders import router as orders_router  # noqa: E402
from app.routers.contracts import router as contracts_router  # noqa: E402
from app.routers.invoices import router as invoices_router  # noqa: E402
from app.routers.dashboard import router as dashboard_router  # noqa: E402
from app.routers.token_tracker import router as token_tracker_router  # noqa: E402
from app.routers.leads import router as leads_router  # noqa: E402
from app.routers.tasks import router as tasks_router  # noqa: E402
from app.routers.time_entries import router as time_entries_router  # noqa: E402
from app.routers.activities import router as activities_router  # noqa: E402
from app.routers.expenses import router as expenses_router  # noqa: E402
from app.routers.euer import router as euer_router  # noqa: E402
from app.routers.backup import router as backup_router  # noqa: E402
from app.routers.attachments import router as attachments_router  # noqa: E402
from app.routers.github import router as github_router  # noqa: E402
from app.routers.email_templates import router as email_templates_router  # noqa: E402
from app.routers.documents import router as documents_router  # noqa: E402
from app.routers.pagespeed import router as pagespeed_router  # noqa: E402
from app.routers.search import router as search_router  # noqa: E402
from app.routers.ical import router as ical_router  # noqa: E402
from app.routers.rainmaker import router as rainmaker_router  # noqa: E402
from app.routers.settings import router as settings_router  # noqa: E402
from app.routers.compliance import router as compliance_router  # noqa: E402
from app.routers.outreach import router as outreach_router  # noqa: E402
from app.routers.suggestions import router as suggestions_router  # noqa: E402
from app.routers.users import router as users_router  # noqa: E402
from app.routers.handoff import router as handoff_router  # noqa: E402
from app.routers.todos import router as todos_router  # noqa: E402

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(contracts_router)
app.include_router(invoices_router)
app.include_router(dashboard_router)
app.include_router(token_tracker_router)
app.include_router(leads_router)
app.include_router(tasks_router)
app.include_router(time_entries_router)
app.include_router(activities_router)
app.include_router(expenses_router)
app.include_router(euer_router)
app.include_router(backup_router)
app.include_router(attachments_router)
app.include_router(github_router)
app.include_router(email_templates_router)
app.include_router(documents_router)
app.include_router(pagespeed_router)
app.include_router(search_router)
app.include_router(ical_router)
app.include_router(rainmaker_router)
app.include_router(settings_router)
app.include_router(compliance_router)
app.include_router(outreach_router)
app.include_router(suggestions_router)
app.include_router(users_router)
app.include_router(handoff_router)
app.include_router(todos_router)


@app.get("/api/health")
async def health_check() -> JSONResponse:
    """Liveness + DB-Connection check. Used by monitoring."""
    from sqlalchemy import text
    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"Health-Check DB-Fehler: {e}")
    payload = {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "sentry": "configured" if settings.SENTRY_DSN else "off",
        "totp": "enabled" if settings.TOTP_SECRET else "disabled",
        "smtp": "configured" if settings.SMTP_HOST else "off",
    }
    return JSONResponse(content=payload, status_code=200 if db_ok else 503)
