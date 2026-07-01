from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.invoice import Invoice

# Offset for externally issued invoices not tracked in this system.
# Set INVOICE_NUMBER_OFFSET in .env to the number of invoices already
# issued outside this app for the current year.
INVOICE_NUMBER_OFFSET = int(getattr(settings, "INVOICE_NUMBER_OFFSET", 0) or 0)


async def generate_invoice_number(db: AsyncSession) -> str:
    year = datetime.now().year
    prefix = f"CO-{year}-"

    # Get all existing numbers for this year
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
    contracts = (
        await db.execute(select(Contract).where(Contract.status == ContractStatus.aktiv))
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
        db.add(Invoice(
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
        ))
        contract.last_invoiced_date = today
        processed.add(contract.id)

    if processed:
        await db.flush()
    return processed
