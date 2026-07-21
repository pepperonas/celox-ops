from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.invoice import Invoice
from app.tenancy import current_owner_id

# Offset for externally issued invoices not tracked in this system.
# Set INVOICE_NUMBER_OFFSET in .env to the number of invoices already
# issued outside this app for the current year.
INVOICE_NUMBER_OFFSET = int(getattr(settings, "INVOICE_NUMBER_OFFSET", 0) or 0)

# Arbitrary namespace constant for the per-owner advisory lock (int4).
_INVOICE_LOCK_NS = 0x1CE0


async def generate_invoice_number(db: AsyncSession) -> str:
    from app.models.app_settings import AppSettings

    # Serialize number generation per owner with a transaction-scoped advisory
    # lock. It is held until commit/rollback, so a concurrent caller (double
    # submit, or cron vs. the manual endpoint) blocks until the first invoice is
    # committed and then reads the fresh max — no duplicate numbers, no retry
    # guessing (which fails under true concurrency because the conflicting row
    # isn't visible until it commits).
    owner = current_owner_id.get()
    if owner is not None:
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:ns, hashtext(:owner))").bindparams(
                ns=_INVOICE_LOCK_NS, owner=str(owner)
            )
        )

    year = datetime.now().year
    # Per-owner prefix (query is owner-scoped via tenancy events; default "CO").
    row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    prefix_code = (row.invoice_prefix if row and row.invoice_prefix else "CO")
    prefix = f"{prefix_code}-{year}-"

    # Get all existing numbers for this year (owner-scoped)
    result = await db.execute(
        select(Invoice.invoice_number)
        .where(Invoice.invoice_number.like(f"{prefix}%"))
    )
    existing = {int(n.split("-")[-1]) for n in result.scalars().all()}

    # Find the first gap starting from offset+1
    next_seq = INVOICE_NUMBER_OFFSET + 1
    while next_seq in existing:
        next_seq += 1

    return f"{prefix}{next_seq:04d}"


CREDIT_NOTE_PREFIX = "GS"


def build_credit_note_positions(positions: list[dict]) -> list[dict]:
    """Positionen der Gutschrift = Spiegelbild des Originals (negative Preise).

    `menge`/`einheit`/`beschreibung` bleiben unverändert — nur Einzelpreis und
    Gesamt kippen ins Negative (`-abs`, damit ein zweifaches Gutschreiben nie
    versehentlich wieder positiv wird). Decimal-sicher über Strings, weil die
    Positionen als JSON liegen und float-Rundung sonst Cent-Fehler erzeugt.
    """
    out: list[dict] = []
    for pos in positions:
        neg = dict(pos)
        for key in ("einzelpreis", "gesamt"):
            if pos.get(key) is None:
                continue
            neg[key] = str(-abs(Decimal(str(pos[key]))))
        out.append(neg)
    return out


def next_credit_note_number(existing: set[int] | list[int], year: int) -> str:
    """Nächste freie Gutschriftnummer `GS-YYYY-NNNN` (eigener Nummernkreis,
    getrennt von den Rechnungsnummern — bei Gutschriften zulässig und üblich).
    Füllt Lücken auf, damit ein gelöschter Entwurf keine Nummer verbrennt."""
    taken = set(existing)
    seq = 1
    while seq in taken:
        seq += 1
    return f"{CREDIT_NOTE_PREFIX}-{year}-{seq:04d}"


def credit_note_statuses(original_status):
    """Statuspaar (Gutschrift, Original) nach dem Storno — so, dass die Zahlen
    in EÜR und Dashboard stimmen.

    - Original **bezahlt**: Geld ist geflossen und fließt zurück → Netting.
      Original bleibt `bezahlt` (+X), Gutschrift wird `bezahlt` (−X). Summe 0,
      der Rückfluss landet im Monat der Gutschrift (Zufluss-/Abflussprinzip).
    - Original **gestellt/überfällig**: es floss nie Geld → Neutralisierung.
      Beide werden `storniert`; `storniert` zählt weder in der EÜR (nur
      `bezahlt`) noch in den offenen Forderungen. Ohne das bliebe die Forderung
      stehen UND die Gutschrift erzeugte einen negativen Umsatz aus dem Nichts.
    """
    from app.models.invoice import InvoiceStatus

    if original_status == InvoiceStatus.bezahlt:
        return InvoiceStatus.bezahlt, InvoiceStatus.bezahlt
    return InvoiceStatus.storniert, InvoiceStatus.storniert


async def generate_credit_note_number(db: AsyncSession) -> str:
    """Owner-scoped Gutschriftnummer, gegen Doppelklick per Advisory Lock
    serialisiert (gleiches Muster wie generate_invoice_number)."""
    owner = current_owner_id.get()
    if owner is not None:
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:ns, hashtext(:owner))").bindparams(
                ns=_INVOICE_LOCK_NS, owner=f"gs:{owner}"
            )
        )
    year = datetime.now().year
    prefix = f"{CREDIT_NOTE_PREFIX}-{year}-"
    result = await db.execute(
        select(Invoice.invoice_number).where(Invoice.invoice_number.like(f"{prefix}%"))
    )
    existing = set()
    for number in result.scalars().all():
        try:
            existing.add(int(number.split("-")[-1]))
        except ValueError:  # pragma: no cover — fremdformatige Altnummer
            continue
    return next_credit_note_number(existing, year)


async def flush_new_invoice(db: AsyncSession, invoice, attempts: int = 3) -> None:
    """Add + flush a new invoice, retrying with a fresh number when a concurrent
    request grabbed the same one (uq_invoice_owner_number). The SAVEPOINT keeps
    the surrounding transaction usable on conflict; without this the race
    surfaces as an unhandled 500."""
    from sqlalchemy.exc import IntegrityError

    for attempt in range(attempts):
        try:
            async with db.begin_nested():
                db.add(invoice)
                await db.flush()
            return
        except IntegrityError:
            if attempt == attempts - 1:
                raise
            invoice.invoice_number = await generate_invoice_number(db)


def calculate_invoice_totals(
    positions: list[dict],
    tax_rate: Decimal,
    tax_exempt: bool,
    discount_type: str | None = None,
    discount_value: float | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    positions_subtotal = Decimal("0.00")
    for pos in positions:
        gesamt = Decimal(str(pos["menge"])) * Decimal(str(pos["einzelpreis"]))
        positions_subtotal += gesamt

    positions_subtotal = positions_subtotal.quantize(Decimal("0.01"))

    # Apply discount
    discount = Decimal("0.00")
    if discount_type and discount_value is not None and discount_value != 0:
        if discount_type == "percent":
            discount = (positions_subtotal * Decimal(str(discount_value)) / Decimal("100")).quantize(Decimal("0.01"))
        else:
            discount = Decimal(str(discount_value)).quantize(Decimal("0.01"))

    subtotal = (positions_subtotal - discount).quantize(Decimal("0.01"))

    if tax_exempt:
        tax_amount = Decimal("0.00")
    else:
        tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))

    total = subtotal + tax_amount
    return subtotal, tax_amount, total


async def generate_due_recurring(db: AsyncSession) -> set:
    """Creates draft invoices for all DUE recurring contract billings of the
    current owner (ContextVar-scoped). Idempotent: advances `last_invoiced_date`
    so a due contract is billed at most once per cycle. Returns the set of
    processed contract ids. Callable from the endpoint and the cron."""
    from datetime import date as date_type
    from datetime import timedelta

    from dateutil.relativedelta import relativedelta

    from app.models.contract import BillingCycle, Contract, ContractStatus
    from app.models.invoice import InvoiceStatus

    today = date_type.today()
    # FOR UPDATE: serialize against a concurrent run (hourly cron vs. the manual
    # "generate" endpoint) — otherwise both read the same last_invoiced_date and
    # create duplicate drafts for the period.
    contracts = (
        await db.execute(
            select(Contract).where(Contract.status == ContractStatus.aktiv).with_for_update()
        )
    ).scalars().unique().all()
    if not contracts:
        return set()

    cycle_months = {
        BillingCycle.monatlich: 1, BillingCycle.quartalsweise: 3,
        BillingCycle.halbjaehrlich: 6, BillingCycle.jaehrlich: 12,
    }
    german_months = [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ]
    processed: set = set()

    for contract in contracts:
        months = cycle_months[contract.billing_cycle]
        if contract.last_invoiced_date is None:
            is_due = True
        else:
            is_due = (contract.last_invoiced_date + relativedelta(months=months)) <= today
        if not is_due:
            continue

        if contract.billing_cycle == BillingCycle.monatlich:
            period_label = f"{german_months[today.month]} {today.year}"
        elif contract.billing_cycle == BillingCycle.quartalsweise:
            period_label = f"Q{(today.month - 1) // 3 + 1} {today.year}"
        elif contract.billing_cycle == BillingCycle.halbjaehrlich:
            period_label = f"{1 if today.month <= 6 else 2}. Halbjahr {today.year}"
        else:
            period_label = str(today.year)

        amount = contract.monthly_amount * Decimal(str(months))
        positions_json = [{
            "position": 1, "beschreibung": contract.title, "menge": "1",
            "einheit": period_label, "einzelpreis": str(amount), "gesamt": str(amount),
        }]
        positions_dicts = [{
            "position": 1, "beschreibung": contract.title, "menge": Decimal("1"),
            "einheit": period_label, "einzelpreis": amount, "gesamt": amount,
        }]
        is_exempt = settings.KLEINUNTERNEHMER
        subtotal, tax_amount, total = calculate_invoice_totals(
            positions_dicts, Decimal("19.00"), is_exempt
        )
        new_invoice = Invoice(
            customer_id=contract.customer_id,
            contract_id=contract.id,
            invoice_number=await generate_invoice_number(db),
            title=f"{contract.title} — {period_label}",
            positions=positions_json,
            subtotal=subtotal,
            tax_rate=Decimal("0") if is_exempt else Decimal("19.00"),
            tax_exempt=is_exempt,
            tax_amount=tax_amount,
            total=total,
            invoice_date=today,
            due_date=today + timedelta(days=14),
            status=InvoiceStatus.entwurf,
        )
        await flush_new_invoice(db, new_invoice)
        contract.last_invoiced_date = today
        processed.add(contract.id)

    if processed:
        await db.flush()
    return processed
