"""Die Rolle „Verkäufer" über die **HTTP-Schicht** — mit echten Tokens.

Die Erlaubnisliste selbst ist DB-frei getestet (`test_role_scope.py`). Hier wird
geprüft, dass die Middleware sie tatsächlich durchsetzt, dass Löschen als
Papierkorb wirkt, dass der Tagesdeckel greift und dass die Aufsicht dem Inhaber
gehört. Ein statisch korrektes Regelwerk, das die Middleware nicht anwendet, wäre
wertlos.

Läuft nur mit `TEST_DATABASE_URL` (siehe conftest).
"""
import uuid

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


def _token(username: str) -> dict[str, str]:
    from app.auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': username})}"}


@pytest_asyncio.fixture(scope="function")
async def client(sessionmaker):
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
async def sales_workspace(sessionmaker):
    """Ein Inhaber mit Kunde + Lead, dazu ein Verkäufer in seinem Bereich."""
    from app.models.customer import Customer
    from app.models.rainmaker_lead import RainmakerLead
    from app.models.user import User, UserRole

    async with sessionmaker() as db:
        boss = User(id=uuid.uuid4(), username="chef", password_hash="x",
                    role=UserRole.user, is_active=True)
        db.add(boss)
        await db.flush()
        sales = User(id=uuid.uuid4(), username="vk", password_hash="x",
                     role=UserRole.verkaeufer, is_active=True, works_for_id=boss.id)
        cust = Customer(id=uuid.uuid4(), name="Geheimkunde", owner_id=boss.id)
        lead = RainmakerLead(id=uuid.uuid4(), owner_id=boss.id, company="Alpha GmbH")
        db.add_all([sales, cust, lead])
        await db.commit()
        return {"boss": boss.id, "sales": sales.id, "customer": cust.id, "lead": lead.id}


# --------------------------------------------------------------------------- #
#  Zuschnitt
# --------------------------------------------------------------------------- #

async def test_pipeline_is_reachable(sales_workspace, client):
    res = await client.get("/api/rainmaker/leads", headers=_token("vk"))
    assert res.status_code == 200
    # Der Verkäufer arbeitet IM Bereich des Chefs — er sieht dessen Leads.
    assert "Alpha GmbH" in res.text


async def test_outreach_templates_are_readable(sales_workspace, client):
    res = await client.get("/api/outreach/templates", headers=_token("vk"))
    assert res.status_code == 200


async def test_rest_of_the_app_is_blocked(sales_workspace, client):
    """Der eigentliche Beweis: deny-by-default greift durch die Middleware."""
    for path in ("/api/customers", "/api/invoices", "/api/expenses", "/api/contracts",
                 "/api/orders", "/api/todos", "/api/dashboard/stats", "/api/settings",
                 "/api/users", "/api/rainmaker/today", "/api/rainmaker/stats",
                 "/api/rainmaker/duplicates", "/api/rainmaker/ai/usage"):
        res = await client.get(path, headers=_token("vk"))
        assert res.status_code == 403, f"{path} → {res.status_code}"
        assert "Verkäufer" in res.text

    # Und der Kundenname taucht nirgends auf.
    res = await client.get(f"/api/customers/{sales_workspace['customer']}", headers=_token("vk"))
    assert res.status_code == 403
    assert "Geheimkunde" not in res.text


async def test_email_and_paid_ai_are_blocked(sales_workspace, client):
    lead = sales_workspace["lead"]
    for path in (f"/api/rainmaker/leads/{lead}/send-email",
                 f"/api/rainmaker/leads/{lead}/draft-email",
                 f"/api/rainmaker/leads/{lead}/analyze-website",
                 "/api/rainmaker/leads/intake",
                 "/api/rainmaker/discover/ai/preview",
                 "/api/rainmaker/import/linkedin"):
        res = await client.post(path, headers=_token("vk"), json={})
        assert res.status_code == 403, f"{path} → {res.status_code}"


async def test_template_writes_are_blocked(sales_workspace, client):
    res = await client.post("/api/outreach/templates", headers=_token("vk"),
                            json={"channel": "email", "category": "kaltakquise",
                                  "title": "X", "body": "Y"})
    assert res.status_code == 403


# --------------------------------------------------------------------------- #
#  Papierkorb
# --------------------------------------------------------------------------- #

async def test_delete_moves_to_trash_instead_of_removing(sales_workspace, client, sessionmaker):
    from sqlalchemy import select

    from app.models.rainmaker_lead import RainmakerLead
    from app.tenancy import soft_deleted_visible

    lead_id = sales_workspace["lead"]
    res = await client.delete(f"/api/rainmaker/leads/{lead_id}", headers=_token("vk"))
    assert res.status_code == 204

    # Aus der Pipeline verschwunden …
    listing = await client.get("/api/rainmaker/leads", headers=_token("vk"))
    assert "Alpha GmbH" not in listing.text
    detail = await client.get(f"/api/rainmaker/leads/{lead_id}", headers=_token("vk"))
    assert detail.status_code == 404

    # … aber die Zeile lebt, markiert und mit Urheber.
    async with sessionmaker() as db:
        with soft_deleted_visible():
            row = (await db.execute(
                select(RainmakerLead).where(RainmakerLead.id == lead_id)
            )).scalar_one()
        assert row.deleted_at is not None
        assert row.deleted_by_id == sales_workspace["sales"]


async def test_owner_sees_trash_and_can_restore(sales_workspace, client):
    lead_id = sales_workspace["lead"]
    await client.delete(f"/api/rainmaker/leads/{lead_id}", headers=_token("vk"))

    trash = await client.get("/api/rainmaker/leads/trash", headers=_token("chef"))
    assert trash.status_code == 200
    body = trash.json()
    assert [i["company"] for i in body["items"]] == ["Alpha GmbH"]
    assert body["items"][0]["deleted_by"] == "vk"
    assert body["items"][0]["days_left"] > 0

    res = await client.post(f"/api/rainmaker/leads/{lead_id}/restore", headers=_token("chef"))
    assert res.status_code == 200
    listing = await client.get("/api/rainmaker/leads", headers=_token("chef"))
    assert "Alpha GmbH" in listing.text


async def test_supervision_is_closed_to_the_supervised_role(sales_workspace, client):
    """Sonst wäre der Papierkorb bloß ein Zwischenschritt beim Löschen."""
    lead_id = sales_workspace["lead"]
    assert (await client.get("/api/rainmaker/leads/trash",
                             headers=_token("vk"))).status_code == 403
    assert (await client.post(f"/api/rainmaker/leads/{lead_id}/restore",
                              headers=_token("vk"))).status_code == 403
    assert (await client.delete(f"/api/rainmaker/leads/{lead_id}/purge",
                                headers=_token("vk"))).status_code == 403
    assert (await client.get("/api/rainmaker/lead-changes",
                             headers=_token("vk"))).status_code == 403


async def test_daily_delete_cap_stops_a_runaway(sales_workspace, client, sessionmaker):
    """Der Deckel muss wirklich greifen — er zählt gelöschte Zeilen, die
    normalerweise ausgefiltert sind (dort lag der Fehler im ersten Entwurf)."""
    from app.models.rainmaker_lead import RainmakerLead
    from app.models.user import VERKAEUFER_DAILY_DELETE_CAP as CAP

    ids = []
    async with sessionmaker() as db:
        for i in range(CAP + 2):
            lead = RainmakerLead(id=uuid.uuid4(), owner_id=sales_workspace["boss"],
                                 company=f"Ziel {i}")
            db.add(lead)
            ids.append(lead.id)
        await db.commit()

    codes = [
        (await client.delete(f"/api/rainmaker/leads/{i}", headers=_token("vk"))).status_code
        for i in ids
    ]
    assert codes[:CAP] == [204] * CAP
    assert codes[CAP] == 429
    assert set(codes[CAP:]) == {429}

    # Der Inhaber selbst unterliegt dem Deckel nicht.
    own = await client.delete(f"/api/rainmaker/leads/{ids[-1]}", headers=_token("chef"))
    assert own.status_code == 204


async def test_reimport_after_delete_is_not_blocked_by_the_unique_index(
    sales_workspace, client, sessionmaker,
):
    """Ein Lead im Papierkorb darf die Firma nicht dauerhaft sperren — sonst
    scheiterte der Wiederimport an einem Datensatz, den niemand sieht."""
    from app.models.rainmaker_lead import RainmakerLead

    async with sessionmaker() as db:
        lead = RainmakerLead(id=uuid.uuid4(), owner_id=sales_workspace["boss"],
                             company="Beta AG", email="kontakt@beta-ag.de")
        db.add(lead)
        await db.commit()
        first = lead.id

    assert (await client.delete(f"/api/rainmaker/leads/{first}",
                                headers=_token("vk"))).status_code == 204

    again = await client.post("/api/rainmaker/leads", headers=_token("vk"),
                              json={"company": "Beta AG", "email": "kontakt@beta-ag.de"})
    assert again.status_code == 201, again.text


# --------------------------------------------------------------------------- #
#  Änderungsprotokoll
# --------------------------------------------------------------------------- #

async def test_changes_are_logged_and_revertible(sales_workspace, client):
    lead_id = sales_workspace["lead"]
    res = await client.put(f"/api/rainmaker/leads/{lead_id}", headers=_token("vk"),
                           json={"company": "Alpha Holding", "notes": "Angebot raus"})
    assert res.status_code == 200

    log = await client.get("/api/rainmaker/lead-changes", headers=_token("chef"))
    assert log.status_code == 200
    entries = log.json()
    update = next(e for e in entries if e["action"] == "update")
    assert update["actor"] == "vk"
    assert update["actor_role"] == "verkaeufer"
    assert update["changes"]["company"] == {"old": "Alpha GmbH", "new": "Alpha Holding"}

    back = await client.post(f"/api/rainmaker/lead-changes/{update['id']}/revert",
                             headers=_token("chef"))
    assert back.status_code == 200
    assert set(back.json()["reverted_fields"]) == {"company", "notes"}

    detail = await client.get(f"/api/rainmaker/leads/{lead_id}", headers=_token("chef"))
    assert detail.json()["company"] == "Alpha GmbH"

    # Zweiter Klick darf nicht erneut anwenden.
    assert (await client.post(f"/api/rainmaker/lead-changes/{update['id']}/revert",
                              headers=_token("chef"))).status_code == 409


async def test_owner_changes_are_not_logged(sales_workspace, client):
    """Sonst wäre die Liste, in der man fremde Arbeit prüft, voll mit eigener."""
    lead_id = sales_workspace["lead"]
    await client.put(f"/api/rainmaker/leads/{lead_id}", headers=_token("chef"),
                     json={"company": "Vom Chef geändert"})
    log = await client.get("/api/rainmaker/lead-changes", headers=_token("chef"))
    assert log.json() == []


async def test_revert_skips_fields_changed_since(sales_workspace, client):
    """Fremde, neuere Arbeit darf eine Rücknahme nicht überschreiben."""
    lead_id = sales_workspace["lead"]
    await client.put(f"/api/rainmaker/leads/{lead_id}", headers=_token("vk"),
                     json={"company": "Zwischenstand", "notes": "vom Verkäufer"})
    # Der Inhaber arbeitet danach am selben Feld weiter.
    await client.put(f"/api/rainmaker/leads/{lead_id}", headers=_token("chef"),
                     json={"company": "Chef-Fassung"})

    entry = next(e for e in (await client.get("/api/rainmaker/lead-changes",
                                              headers=_token("chef"))).json()
                 if e["action"] == "update")
    res = await client.post(f"/api/rainmaker/lead-changes/{entry['id']}/revert",
                            headers=_token("chef"))
    assert res.status_code == 200
    assert res.json()["skipped_fields"] == ["company"]
    assert res.json()["reverted_fields"] == ["notes"]

    detail = await client.get(f"/api/rainmaker/leads/{lead_id}", headers=_token("chef"))
    assert detail.json()["company"] == "Chef-Fassung"    # Arbeit des Chefs steht


async def test_deactivated_sales_user_loses_access_immediately(sales_workspace, client,
                                                               sessionmaker):
    from sqlalchemy import update

    from app.models.user import User

    async with sessionmaker() as db:
        await db.execute(update(User).where(User.username == "vk").values(is_active=False))
        await db.commit()

    res = await client.get("/api/rainmaker/leads", headers=_token("vk"))
    assert res.status_code == 401
