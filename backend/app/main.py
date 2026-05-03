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
from app.models.customer import Base
import app.models.pagespeed_result  # noqa: F401 — register for create_all
import app.models.audit_log  # noqa: F401 — register for create_all
from app.middleware.audit import AuditMiddleware
from app.services.cron_service import check_overdue_invoices

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
                        logger.info("Cron: %d Rechnungen als überfällig markiert", count)
                except Exception:
                    await db.rollback()
                    logger.exception("Cron: Fehler bei Überprüfung überfälliger Rechnungen")
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
