import io
import csv
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.expense import Expense

router = APIRouter(
    prefix="/api/euer",
    tags=["euer"],
    dependencies=[Depends(get_current_user)],
)

MONTH_LABELS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

CATEGORY_LABELS: dict[str, str] = {
    "hosting": "Hosting",
    "domain": "Domain",
    "software": "Software",
    "lizenz": "Lizenz",
    "hardware": "Hardware",
    "ki_api": "KI/API",
    "werbung": "Werbung",
    "buero": "Büro",
    "reise": "Reise",
    "sonstige": "Sonstige",
}


async def _build_overview(year: int, db: AsyncSession) -> dict:
    # Revenue by month (paid invoices)
    rev_query = (
        select(
            extract("month", Invoice.invoice_date).label("month"),
            func.sum(Invoice.total).label("total"),
        )
        .where(Invoice.status == InvoiceStatus.bezahlt)
        .where(extract("year", Invoice.invoice_date) == year)
        .group_by(extract("month", Invoice.invoice_date))
    )
    rev_result = await db.execute(rev_query)
    rev_by_month_raw = {int(row.month): float(row.total) for row in rev_result.all()}

    # Expenses by month
    exp_query = (
        select(
            extract("month", Expense.date).label("month"),
            func.sum(Expense.amount).label("total"),
        )
        .where(extract("year", Expense.date) == year)
        .group_by(extract("month", Expense.date))
    )
    exp_result = await db.execute(exp_query)
    exp_by_month_raw = {int(row.month): float(row.total) for row in exp_result.all()}

    # Expenses by category
    cat_query = (
        select(
            Expense.category,
            func.sum(Expense.amount).label("total"),
        )
        .where(extract("year", Expense.date) == year)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    )
    cat_result = await db.execute(cat_query)
    expenses_by_category = [
        {
            "category": row.category.value,
            "label": CATEGORY_LABELS.get(row.category.value, row.category.value),
            "amount": float(row.total),
        }
        for row in cat_result.all()
    ]

    # Build monthly arrays
    revenue_by_month = []
    expenses_by_month = []
    for m in range(1, 13):
        revenue_by_month.append({
            "month": m,
            "label": MONTH_LABELS[m - 1],
            "amount": rev_by_month_raw.get(m, 0.0),
        })
        expenses_by_month.append({
            "month": m,
            "label": MONTH_LABELS[m - 1],
            "amount": exp_by_month_raw.get(m, 0.0),
        })

    # Quarterly
    quarterly = []
    for q in range(4):
        months = [q * 3 + 1, q * 3 + 2, q * 3 + 3]
        q_rev = sum(rev_by_month_raw.get(m, 0.0) for m in months)
        q_exp = sum(exp_by_month_raw.get(m, 0.0) for m in months)
        quarterly.append({
            "quarter": q + 1,
            "label": f"Q{q + 1}",
            "revenue": round(q_rev, 2),
            "expenses": round(q_exp, 2),
            "profit": round(q_rev - q_exp, 2),
        })

    revenue_total = round(sum(r["amount"] for r in revenue_by_month), 2)
    expenses_total = round(sum(e["amount"] for e in expenses_by_month), 2)

    return {
        "year": year,
        "revenue_total": revenue_total,
        "expenses_total": expenses_total,
        "profit": round(revenue_total - expenses_total, 2),
        "revenue_by_month": revenue_by_month,
        "expenses_by_month": expenses_by_month,
        "expenses_by_category": expenses_by_category,
        "quarterly": quarterly,
    }


@router.get("/overview")
async def euer_overview(
    year: int = Query(default_factory=lambda: date.today().year),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await _build_overview(year, db)


@router.get("/export")
async def euer_export(
    year: int = Query(default_factory=lambda: date.today().year),
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    data = await _build_overview(year, db)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Monat", "Einnahmen", "Ausgaben", "Gewinn"])

    for i in range(12):
        rev = data["revenue_by_month"][i]["amount"]
        exp = data["expenses_by_month"][i]["amount"]
        profit = round(rev - exp, 2)
        writer.writerow([
            MONTH_LABELS[i],
            f"{rev:.2f}",
            f"{exp:.2f}",
            f"{profit:.2f}",
        ])

    # Totals row
    writer.writerow([
        "Gesamt",
        f"{data['revenue_total']:.2f}",
        f"{data['expenses_total']:.2f}",
        f"{data['profit']:.2f}",
    ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="euer_{year}.csv"',
        },
    )


@router.get("/forecast")
async def tax_forecast(
    year: int = Query(default=date.today().year),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Steuerprognose: hochrechnung Jahresende basierend auf YTD-Daten + simple Steuersatz-Schätzung.
    Annahmen:
    - YTD-Profit linear hochgerechnet auf Jahresende
    - Vereinfachte ESt-Schätzung mit progressivem Tarif
    - Solidaritätszuschlag entfällt (über Bagatellgrenze)
    """
    today = date.today()
    is_current_year = year == today.year

    # YTD revenue (paid)
    res = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.bezahlt,
            extract("year", Invoice.invoice_date) == year,
        )
    )
    revenue_ytd = float(res.scalar_one() or 0)

    # YTD expenses
    res = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            extract("year", Expense.date) == year,
        )
    )
    expenses_ytd = float(res.scalar_one() or 0)

    profit_ytd = revenue_ytd - expenses_ytd

    # Linear projection to end-of-year
    if is_current_year:
        days_passed = today.timetuple().tm_yday
        days_in_year = 366 if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0 else 365
        factor = days_in_year / max(days_passed, 1)
    else:
        factor = 1.0

    revenue_projected = revenue_ytd * factor
    expenses_projected = expenses_ytd * factor
    profit_projected = profit_ytd * factor

    # Simplified German income tax (Grundtarif 2024/2025 — for prognose only, NO tax advice!)
    # Source: § 32a EStG (Tarif 2024)
    grundfreibetrag = 11604.0
    def estimate_est(profit: float) -> float:
        if profit <= grundfreibetrag:
            return 0.0
        if profit <= 17005:
            y = (profit - grundfreibetrag) / 10000.0
            return (922.98 * y + 1400.0) * y
        if profit <= 66760:
            z = (profit - 17005) / 10000.0
            return (181.19 * z + 2397.0) * z + 1025.38
        if profit <= 277825:
            return 0.42 * profit - 10602.13
        return 0.45 * profit - 18936.88

    est_estimated = estimate_est(profit_projected)
    # USt-Pre-payment liability (only relevant if not Kleinunternehmer)
    # Vereinfachung: Brutto-Rechnungs-Sum minus 100/119 = USt-Anteil; minus Vorsteuer aus Ausgaben
    # Nicht implementiert — erfordert detaillierte Erfassung mit/ohne USt-Ausweis
    return {
        "year": year,
        "ytd": {
            "revenue": round(revenue_ytd, 2),
            "expenses": round(expenses_ytd, 2),
            "profit": round(profit_ytd, 2),
        },
        "projected": {
            "revenue": round(revenue_projected, 2),
            "expenses": round(expenses_projected, 2),
            "profit": round(profit_projected, 2),
            "income_tax_estimate": round(est_estimated, 2),
            "after_tax": round(profit_projected - est_estimated, 2),
        },
        "factor": round(factor, 3),
        "is_current_year": is_current_year,
        "disclaimer": (
            "Schätzung nach Grundtarif § 32a EStG ohne Werbungskosten/Sonderausgaben/Vorsorge. "
            "Keine Steuerberatung — bei tatsächlicher Steuerlast Steuerberater konsultieren."
        ),
    }
