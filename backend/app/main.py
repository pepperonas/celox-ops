import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import async_session_factory, engine
from app.models.customer import Base
from app.services.cron_service import check_overdue_invoices

logger = logging.getLogger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
