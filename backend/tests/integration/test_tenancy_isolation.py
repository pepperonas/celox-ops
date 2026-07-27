"""Integrationstests der Mandantentrennung gegen eine echte Postgres.

Geprüft wird `app/tenancy.py` — 63 Zeilen Session-Events, die als einziger
Mechanismus verhindern, dass Daten eines Arbeitsbereichs in einem anderen
auftauchen. Jeder Test hält außerdem eine **Invariante** fest, auf die sich
Router-Code verlässt (und die in CLAUDE.md dokumentiert ist).

Skippt ohne `TEST_DATABASE_URL` (siehe conftest.py).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy import update as sa_update

pytestmark = pytest.mark.asyncio


async def _customer(db, name: str):
    from app.models.customer import Customer

    c = Customer(name=name, email=f"{name.lower()}@example.test")
    db.add(c)
    await db.flush()
    return c


async def _invoice(db, customer_id, number: str, total="100.00"):
    from app.models.invoice import Invoice, InvoiceStatus

    inv = Invoice(
        customer_id=customer_id, invoice_number=number, title="Leistung",
        positions=[], subtotal=Decimal(total), tax_rate=Decimal("19.00"),
        tax_amount=Decimal("0.00"), total=Decimal(total),
        invoice_date=date(2026, 7, 1), due_date=date(2026, 7, 15),
        status=InvoiceStatus.bezahlt,
    )
    db.add(inv)
    await db.flush()
    return inv


# --------------------------------------------------------------------------- #
#  Kern: Lesen ist auf den eigenen Bereich beschränkt
# --------------------------------------------------------------------------- #
async def test_selects_are_scoped_to_the_owner(sessionmaker, two_users):
    from app.models.customer import Customer
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(a)
        await _customer(db, "AlphaKunde")
        await db.commit()
        current_owner_id.reset(tok)

        tok = current_owner_id.set(b)
        await _customer(db, "BetaKunde")
        await db.commit()

        names = (await db.execute(select(Customer.name))).scalars().all()
        assert names == ["BetaKunde"], "B darf A's Kunden nicht sehen"
        current_owner_id.reset(tok)

        tok = current_owner_id.set(a)
        names = (await db.execute(select(Customer.name))).scalars().all()
        assert names == ["AlphaKunde"]
        current_owner_id.reset(tok)


async def test_new_rows_are_stamped_with_the_owner(sessionmaker, two_users):
    from app.tenancy import current_owner_id

    a, _ = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(a)
        c = await _customer(db, "GestempeltGmbH")
        await db.commit()
        current_owner_id.reset(tok)
    assert c.owner_id == a, "before_flush muss owner_id automatisch setzen"


async def test_direct_id_lookup_of_foreign_row_returns_none(sessionmaker, two_users):
    """Die Invariante hinter jedem `_get_..._or_404`: eine fremde ID ist nicht
    nur unsichtbar in Listen, sondern auch per Direktzugriff."""
    from app.models.customer import Customer
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(b)
        foreign = await _customer(db, "FremdKunde")
        await db.commit()
        current_owner_id.reset(tok)

        tok = current_owner_id.set(a)
        found = (await db.execute(
            select(Customer).where(Customer.id == foreign.id))).scalar_one_or_none()
        assert found is None
        current_owner_id.reset(tok)


async def test_aggregates_are_scoped(sessionmaker, two_users):
    """Dashboard/EÜR rechnen über Aggregate — auch die müssen gescopet sein,
    sonst wäre fremder Umsatz in den eigenen Zahlen."""
    from app.models.invoice import Invoice
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(a)
        ca = await _customer(db, "AUmsatz")
        await _invoice(db, ca.id, "CO-2026-0001", "1000.00")
        await db.commit()
        current_owner_id.reset(tok)

        tok = current_owner_id.set(b)
        cb = await _customer(db, "BUmsatz")
        await _invoice(db, cb.id, "CO-2026-0001", "7777.00")
        await db.commit()

        total = (await db.execute(
            select(func.coalesce(func.sum(Invoice.total), 0)))).scalar_one()
        assert Decimal(total) == Decimal("7777.00"), "B sieht nur den eigenen Umsatz"
        count = (await db.execute(select(func.count()).select_from(Invoice))).scalar_one()
        assert count == 1
        current_owner_id.reset(tok)


# --------------------------------------------------------------------------- #
#  Rechnungsnummern: eigener Kreis pro Bereich
# --------------------------------------------------------------------------- #
async def test_invoice_numbers_are_per_owner(sessionmaker, two_users):
    """`uq_invoice_owner_number` ist pro Owner unique — beide Bereiche dürfen
    dieselbe Nummer führen, und jeder beginnt bei 0001."""
    from app.services.invoice_service import generate_invoice_number
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(a)
        ca = await _customer(db, "AKreis")
        first_a = await generate_invoice_number(db)
        await _invoice(db, ca.id, first_a)
        await db.commit()
        second_a = await generate_invoice_number(db)
        await db.rollback()
        current_owner_id.reset(tok)

        tok = current_owner_id.set(b)
        first_b = await generate_invoice_number(db)
        current_owner_id.reset(tok)

    assert first_a.endswith("-0001")
    assert second_a.endswith("-0002"), "innerhalb eines Bereichs zählt die Nummer hoch"
    assert first_b == first_a, "ein anderer Bereich beginnt wieder bei 0001"


# --------------------------------------------------------------------------- #
#  Dokumentierte Grenzen — hier verlässt sich Router-Code auf eigene Prüfungen
# --------------------------------------------------------------------------- #
async def test_unset_contextvar_sees_everything(sessionmaker, two_users):
    """Cron, Bootstrap und der Analyse-Worker laufen ohne Owner — bewusst
    global. Genau deshalb muss jeder öffentliche Endpunkt (iCal) und jeder
    Worker-Job den ContextVar selbst setzen."""
    from app.models.customer import Customer
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        for owner, name in ((a, "GlobalA"), (b, "GlobalB")):
            tok = current_owner_id.set(owner)
            await _customer(db, name)
            await db.commit()
            current_owner_id.reset(tok)

        assert current_owner_id.get() is None
        names = set((await db.execute(select(Customer.name))).scalars().all())
        assert names == {"GlobalA", "GlobalB"}


async def test_bulk_update_is_not_scoped(sessionmaker, two_users):
    """**Wichtige Invariante:** UPDATE-Statements laufen NICHT durch die
    SELECT-Events. `services/reference_data.py` filtert deshalb explizit auf
    `owner_id` — dieser Test hält fest, warum das kein Schmuck ist."""
    from app.models.customer import Customer
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        for owner, name in ((a, "BulkA"), (b, "BulkB")):
            tok = current_owner_id.set(owner)
            await _customer(db, name)
            await db.commit()
            current_owner_id.reset(tok)

        # Ohne owner_id-Filter trifft ein Bulk-UPDATE als A AUCH die Zeile von B.
        tok = current_owner_id.set(a)
        await db.execute(sa_update(Customer).values(notes="Ueberall"))
        await db.commit()
        current_owner_id.reset(tok)

        rows = (await db.execute(select(Customer.name, Customer.notes))).all()
        assert all(note == "Ueberall" for _, note in rows), (
            "Bulk-UPDATE ist ungescopet — Services MÜSSEN owner_id selbst filtern")

        # Mit explizitem Filter bleibt es korrekt.
        await db.execute(sa_update(Customer).where(Customer.owner_id == a).values(notes="NurA"))
        await db.commit()
        by_name = dict((await db.execute(select(Customer.name, Customer.notes))).all())
        assert by_name["BulkA"] == "NurA" and by_name["BulkB"] == "Ueberall"


async def test_foreign_fk_assignment_is_not_blocked_by_scoping(sessionmaker, two_users):
    """`with_loader_criteria` versteckt Zeilen beim SELECT, es validiert keine
    INSERTs. Ein Request mit fremder `customer_id` würde also durchgehen —
    deshalb prüfen die Router jede FK-ID vorher mit einem gescopten Select."""
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(b)
        foreign = await _customer(db, "FremdFK")
        await db.commit()
        current_owner_id.reset(tok)

        tok = current_owner_id.set(a)
        inv = await _invoice(db, foreign.id, "CO-2026-0009")
        await db.commit()
        # Die Datenbank akzeptiert es (FK ist gültig) → die Prüfung im Router
        # ist der einzige Schutz. Der gescopte Select findet die ID nicht:
        from app.models.customer import Customer
        assert (await db.execute(
            select(Customer.id).where(Customer.id == foreign.id))).scalar_one_or_none() is None
        assert inv.customer_id == foreign.id
        current_owner_id.reset(tok)


async def test_every_owned_model_actually_has_owner_id(sessionmaker):
    """Regressionsguard: ein in `set_owned_models` eingetragenes Modell ohne
    `owner_id`-Spalte würde die Filterung stumm sprengen."""
    from app.tenancy import _owned_models

    assert len(_owned_models) >= 25
    for model in _owned_models:
        assert "owner_id" in model.__table__.columns, model.__name__


async def test_owner_delete_cascades(sessionmaker, two_users):
    """`ON DELETE CASCADE` am owner_id-FK: ein gelöschter Nutzer hinterlässt
    keine verwaisten, plötzlich globalen Datensätze."""
    from sqlalchemy import delete as sa_delete

    from app.models.customer import Customer
    from app.models.user import User
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        for owner, name in ((a, "CascA"), (b, "CascB")):
            tok = current_owner_id.set(owner)
            await _customer(db, name)
            await db.commit()
            current_owner_id.reset(tok)

        await db.execute(sa_delete(User).where(User.id == a))
        await db.commit()

        names = set((await db.execute(select(Customer.name))).scalars().all())
        assert names == {"CascB"}, "A's Daten müssen mit A verschwinden"


async def test_session_get_is_also_scoped(sessionmaker, two_users):
    """`db.get()` ist ein Primärschlüssel-Zugriff — Router-Code (documents.py,
    compliance.py, github.py) verlässt sich darauf, dass die Mandantenfilterung
    auch dort greift. Bisher stand das nur als Kommentar im Code; hier ist es
    festgenagelt.
    """
    from app.models.customer import Customer
    from app.tenancy import current_owner_id

    a, b = two_users
    async with sessionmaker() as db:
        tok = current_owner_id.set(b)
        foreign = await _customer(db, "FremdGet")
        await db.commit()
        current_owner_id.reset(tok)

    # Frische Session: kein Treffer im Identity-Map, es muss wirklich SQL laufen.
    async with sessionmaker() as db:
        tok = current_owner_id.set(a)
        assert await db.get(Customer, foreign.id) is None
        current_owner_id.reset(tok)

    # Und als Eigentümer findet er sie natürlich.
    async with sessionmaker() as db:
        tok = current_owner_id.set(b)
        assert (await db.get(Customer, foreign.id)).name == "FremdGet"
        current_owner_id.reset(tok)
