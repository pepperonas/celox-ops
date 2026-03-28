from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models.customer import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


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


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
