from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice


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
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


def calculate_invoice_totals(
    positions: list[dict],
    tax_rate: Decimal,
    kleinunternehmer: bool,
) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = Decimal("0.00")
    for pos in positions:
        gesamt = Decimal(str(pos["menge"])) * Decimal(str(pos["einzelpreis"]))
        subtotal += gesamt

    subtotal = subtotal.quantize(Decimal("0.01"))

    if kleinunternehmer:
        tax_amount = Decimal("0.00")
    else:
        tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))

    total = subtotal + tax_amount
    return subtotal, tax_amount, total
