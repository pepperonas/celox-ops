"""Bereichsübergreifende Zugriffe über die **HTTP-Schicht** — mit echten Tokens.

Warum zusätzlich zu `test_tenancy_isolation.py`: dort wird der Mechanismus geprüft
(Session-Events, Stempeln, `db.get`, Grenzen). Hier wird geprüft, was ein fremder
Nutzer **durch die API** tatsächlich erreicht — inklusive der Router-Logik, die auf
dem Mechanismus aufsetzt: Direktzugriff per ID, Dateiausgabe, Mutationen, Löschen
und das Unterschieben fremder Fremdschlüssel.

Dieser Test ist die dauerhafte Fassung eines manuellen Angriffslaufs gegen die
Produktion (2026-07-28, ~50 Versuche, 0 Lecks). Ohne ihn müsste das jemand von
Hand wiederholen — und würde es nicht.

Läuft nur mit `TEST_DATABASE_URL` (siehe conftest).
"""
import uuid

import pytest
import pytest_asyncio

# Wie in test_tenancy_isolation.py: pytest-asyncio, NICHT anyio — sonst laufen
# Fixture und Test in verschiedenen Event-Loops und asyncpg bricht ab
# ("attached to a different loop").
pytestmark = pytest.mark.asyncio


def _token(username: str) -> dict[str, str]:
    from app.auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': username})}"}


@pytest_asyncio.fixture(scope="function")
async def client(sessionmaker):
    """ASGI-Client gegen die echte App (keine Netzwerkschicht).

    `get_db` wird auf die Test-Datenbank umgebogen — ohne das griffe die App auf
    ihre konfigurierte `DATABASE_URL` zu (im Container `db:5432`), die hier nicht
    läuft. Die Ersetzung spiegelt das Original inklusive commit/rollback, damit
    das Transaktionsverhalten der Router unverändert bleibt.
    """
    import httpx

    from app.database import get_db
    from app.main import app

    async def _override():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test", timeout=30) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(scope="function")
async def two_workspaces(sessionmaker):
    """Zwei Inhaber mit je einem Kunden, einer Rechnung, einer Ausgabe, einem Lead."""
    from decimal import Decimal

    from app.models.customer import Customer
    from app.models.expense import Expense, ExpenseCategory
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.rainmaker_lead import RainmakerLead
    from app.models.user import User, UserRole
    from app.services.business_time import today

    made = {}
    async with sessionmaker() as db:
        for name in ("owner_a", "owner_b"):
            user = User(id=uuid.uuid4(), username=name, password_hash="x",
                        role=UserRole.user, is_active=True, ical_token=uuid.uuid4().hex)
            db.add(user)
            await db.flush()
            cust = Customer(id=uuid.uuid4(), name=f"Kunde {name}", owner_id=user.id)
            inv = Invoice(id=uuid.uuid4(), customer_id=cust.id, owner_id=user.id,
                          invoice_number=f"X-{name}", title="T", invoice_date=today(),
                          due_date=today(), subtotal=Decimal("100.00"),
                          tax_rate=Decimal("0"), tax_amount=Decimal("0"),
                          total=Decimal("100.00"), status=InvoiceStatus.gestellt)
            exp = Expense(id=uuid.uuid4(), owner_id=user.id, description=f"Ausgabe {name}",
                          category=ExpenseCategory.hosting, amount=Decimal("10.00"),
                          date=today())
            lead = RainmakerLead(id=uuid.uuid4(), owner_id=user.id, company=f"Firma {name}")
            db.add_all([cust, inv, exp, lead])
            await db.commit()
            made[name] = {"user": user.id, "customer": cust.id, "invoice": inv.id,
                          "expense": exp.id, "lead": lead.id}
    return made


async def test_lists_never_contain_the_other_workspace(two_workspaces, client):
    """Der Einstiegspunkt: Listen zeigen ausschließlich eigene Zeilen."""
    for path in ("/api/customers", "/api/invoices", "/api/expenses",
                 "/api/rainmaker/leads"):
        res = await client.get(path, headers=_token("owner_b"))
        assert res.status_code == 200, path
        body = res.json()
        assert body["total"] == 1, f"{path}: {body['total']} statt 1"
        assert "owner_a" not in res.text, f"{path} zeigt fremde Daten"


async def test_direct_access_to_foreign_rows_is_404(two_workspaces, client):
    """404, nicht 403: ein fremder Datensatz existiert für diesen Nutzer nicht —
    das verrät auch nicht, DASS er existiert."""
    a = two_workspaces["owner_a"]
    for path in (f"/api/customers/{a['customer']}",
                 f"/api/invoices/{a['invoice']}",
                 f"/api/expenses/{a['expense']}",
                 f"/api/rainmaker/leads/{a['lead']}",
                 f"/api/invoices/{a['invoice']}/pdf"):
        res = await client.get(path, headers=_token("owner_b"))
        assert res.status_code == 404, f"{path} → {res.status_code}"


async def test_foreign_rows_cannot_be_changed_or_deleted(two_workspaces, sessionmaker, client):
    from sqlalchemy import select

    from app.models.customer import Customer
    from app.tenancy import current_owner_id

    a = two_workspaces["owner_a"]
    h = _token("owner_b")
    assert (await client.put(f"/api/customers/{a['customer']}", headers=h,
                             json={"name": "GEKAPERT"})).status_code == 404
    assert (await client.put(f"/api/expenses/{a['expense']}", headers=h,
                             json={"description": "GEKAPERT"})).status_code == 404
    for path in (f"/api/customers/{a['customer']}", f"/api/expenses/{a['expense']}",
                 f"/api/rainmaker/leads/{a['lead']}", f"/api/invoices/{a['invoice']}"):
        assert (await client.request("DELETE", path, headers=h)).status_code == 404, path

    # Und der Datensatz steht unverändert da.
    async with sessionmaker() as db:
        token = current_owner_id.set(a["user"])
        cust = (await db.execute(select(Customer).where(
            Customer.id == a["customer"]))).scalar_one()
        assert cust.name == "Kunde owner_a"
        current_owner_id.reset(token)


async def test_foreign_foreign_keys_are_refused(two_workspaces, client):
    """Die wichtigste Router-Pflicht: `with_loader_criteria` validiert KEINE
    INSERTs. Wer eine fremde ID im Body akzeptiert, ohne sie gescopet zu prüfen,
    verknüpft Daten über Bereichsgrenzen — und leakt sie in Antwort und PDF."""
    a = two_workspaces["owner_a"]
    h = _token("owner_b")
    res = await client.post("/api/invoices", headers=h, json={
        "customer_id": str(a["customer"]), "title": "Unterschoben",
        "invoice_date": "2026-07-28", "due_date": "2026-08-28",
        "positions": [], "tax_rate": 19})
    assert res.status_code == 404, f"fremde customer_id akzeptiert: {res.status_code}"
    res = await client.post("/api/todos", headers=h, json={
        "title": "Unterschoben", "customer_id": str(a["customer"])})
    assert res.status_code == 404


async def test_ical_feed_is_bound_to_its_token(two_workspaces, sessionmaker, client):
    """Der iCal-Feed ist der einzige Endpunkt ohne JWT — er MUSS den Bereich aus
    dem Token auflösen, sonst wäre er ein offenes Fenster."""
    from sqlalchemy import select

    from app.models.user import User

    async with sessionmaker() as db:
        tokens = {u.username: u.ical_token for u in
                  (await db.execute(select(User))).scalars().all()}
    assert (await client.get("/api/ical?token=falsch")).status_code == 403
    feed_b = await client.get(f"/api/ical?token={tokens['owner_b']}")
    assert feed_b.status_code == 200
    assert "X-owner_a" not in feed_b.text        # fremde Rechnungsnummer
    assert "X-owner_b" in feed_b.text            # die eigene schon


async def test_deactivating_a_user_invalidates_existing_tokens(two_workspaces, sessionmaker, client):
    """Die Rolle und der Zustand werden pro Anfrage gegen die DB geprüft — sonst
    würde eine Sperre erst mit dem Token-Ablauf greifen (bis 24 h)."""
    from sqlalchemy import select

    from app.models.user import User

    header = _token("owner_b")
    assert (await client.get("/api/customers", headers=header)).status_code == 200
    async with sessionmaker() as db:
        user = (await db.execute(select(User).where(
            User.username == "owner_b"))).scalar_one()
        user.is_active = False
        await db.commit()
    assert (await client.get("/api/customers", headers=header)).status_code == 401
