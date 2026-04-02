from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
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

    result = await db.execute(
        select(Invoice.invoice_number)
        .where(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .limit(1)
    )
    last_number = result.scalar_one_or_none()

    if last_number:
        last_seq = int(last_number.split("-")[-1])
        next_seq = last_seq + 1
    else:
        next_seq = INVOICE_NUMBER_OFFSET + 1

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
    if discount_type and discount_value:
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
