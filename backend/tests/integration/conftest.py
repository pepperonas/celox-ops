"""Setup für die Integrationstests gegen eine echte Postgres.

Diese Tests sind die Ausnahme von der Repo-Regel „alle Tests DB-frei": die
Mandantentrennung lebt in SQLAlchemy-Session-Events (`app/tenancy.py`) und lässt
sich ohne echte Datenbank nicht ehrlich prüfen — genau dort wäre ein Fehler aber
am teuersten (fremde Kundendaten im PDF).

Läuft nur, wenn `TEST_DATABASE_URL` gesetzt ist; sonst werden alle Tests
übersprungen (lokal ohne DB, und die bestehende CI bleibt unverändert grün).

**Sicherung:** der Datenbankname MUSS „test" enthalten. Diese Datei ruft
`drop_all`/`create_all` — ein versehentlich gesetzter Prod-Connection-String
würde sonst die Geschäftsdaten löschen.

Start einer Wegwerf-DB lokal:
    docker run --rm -d -p 5544:5432 -e POSTGRES_PASSWORD=test \\
        -e POSTGRES_USER=test -e POSTGRES_DB=celoxops_test --name ops-testdb postgres:16
    export TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5544/celoxops_test
"""
import os
import uuid

import pytest
import pytest_asyncio

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL nicht gesetzt")


def _guard_test_database(url: str) -> None:
    """Niemals gegen eine Datenbank ohne „test" im Namen arbeiten."""
    dbname = url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in dbname.lower():
        raise RuntimeError(
            f"Sicherheitsstopp: TEST_DATABASE_URL zeigt auf '{dbname}'. Diese Tests "
            "löschen und legen alle Tabellen neu an — der Datenbankname muss 'test' "
            "enthalten."
        )


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL nicht gesetzt")
    _guard_test_database(TEST_DB_URL)

    from sqlalchemy.ext.asyncio import create_async_engine

    # app.main importieren registriert ALLE Modelle und installiert die
    # Tenancy-Events — die Tests prüfen damit die echte Verdrahtung
    # (inkl. der `set_owned_models`-Liste), nicht einen Nachbau.
    os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
    os.environ.setdefault("JWT_SECRET", "integration-test-secret-at-least-32-chars-long")
    os.environ.setdefault("ADMIN_USERNAME", "admin")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost")
    import app.main  # noqa: F401
    from app.models.customer import Base

    engine = create_async_engine(TEST_DB_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def sessionmaker(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def two_users(sessionmaker):
    """Zwei getrennte Arbeitsbereiche (A und B) — global angelegt (users ist
    nicht owner-scoped), ohne gesetzten ContextVar."""
    from app.models.user import User, UserRole

    a = User(id=uuid.uuid4(), username="alice", password_hash="x",
             role=UserRole.user, is_active=True, ical_token=uuid.uuid4().hex)
    b = User(id=uuid.uuid4(), username="bob", password_hash="x",
             role=UserRole.user, is_active=True, ical_token=uuid.uuid4().hex)
    async with sessionmaker() as db:
        db.add_all([a, b])
        await db.commit()
    return a.id, b.id
