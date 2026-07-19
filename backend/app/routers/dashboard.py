import asyncio
import calendar
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from weasyprint import HTML

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.tenancy import current_owner_id
from app.models.activity import Activity
from app.models.contract import Contract, ContractStatus
from app.models.customer import Customer
from app.models.expense import Expense
from app.models.invoice import Invoice, InvoiceStatus
from app.models.lead import Lead, LeadStatus
from app.models.order import Order, OrderStatus
from app.models.time_entry import TimeEntry
from app.services.filenames import download_name

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


class CustomerProfitability(BaseModel):
    customer_id: str
    customer_name: str
    revenue: float
    expenses: float
    hours_logged: float
    ai_hours: float
    invoices_count: int
    effective_hourly_rate: float
    profit: float


class ForecastData(BaseModel):
    monthly_recurring: float
    annual_recurring: float
    pipeline_value: float
    pipeline_count: int
    forecast_3m: float
    forecast_6m: float
    forecast_12m: float
    leads_count: int


class DashboardStats(BaseModel):
    revenue_month: Decimal
    revenue_year: Decimal
    draft_invoices_count: int
    draft_invoices_sum: Decimal
    open_invoices_count: int
    open_invoices_sum: Decimal
    overdue_invoices_count: int
    overdue_invoices_sum: Decimal
    active_contracts_count: int
    active_contracts_monthly_sum: Decimal


# In-memory caches: 60-second TTL, keyed per user (multi-tenant).
_stats_cache: dict = {}
_charts_cache: dict = {}  # keyed by (owner_id, period, include_drafts)
_STATS_CACHE_TTL = 60.0


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """Half-open [start, end) for a given month — sargable (uses the date index)."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    oid = current_owner_id.get()
    entry = _stats_cache.get(oid)
    if entry is not None and time.monotonic() < entry["expires"]:
        return entry["data"]

    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    today = date.today()

    _m_start, _m_end = _month_bounds(current_year, current_month)
    _y_start, _y_end = date(current_year, 1, 1), date(current_year + 1, 1, 1)

    # Revenue this month (paid invoices)
    result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.bezahlt,
            Invoice.invoice_date >= _m_start,
            Invoice.invoice_date < _m_end,
        )
    )
    revenue_month = result.scalar_one()

    # Revenue this year
    result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.bezahlt,
            Invoice.invoice_date >= _y_start,
            Invoice.invoice_date < _y_end,
        )
    )
    revenue_year = result.scalar_one()

    # Draft invoices (entwurf)
    result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.entwurf,
        )
    )
    row = result.one()
    draft_invoices_count = row[0]
    draft_invoices_sum = row[1]

    # Open invoices (gestellt)
    result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.gestellt,
        )
    )
    row = result.one()
    open_invoices_count = row[0]
    open_invoices_sum = row[1]

    # Overdue invoices
    result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status.in_([InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig]),
            Invoice.due_date < today,
        )
    )
    row = result.one()
    overdue_invoices_count = row[0]
    overdue_invoices_sum = row[1]

    # Active contracts
    result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Contract.monthly_amount), 0),
        ).where(Contract.status == ContractStatus.aktiv)
    )
    row = result.one()
    active_contracts_count = row[0]
    active_contracts_monthly_sum = row[1]

    stats = DashboardStats(
        revenue_month=revenue_month,
        revenue_year=revenue_year,
        draft_invoices_count=draft_invoices_count,
        draft_invoices_sum=draft_invoices_sum,
        open_invoices_count=open_invoices_count,
        open_invoices_sum=open_invoices_sum,
        overdue_invoices_count=overdue_invoices_count,
        overdue_invoices_sum=overdue_invoices_sum,
        active_contracts_count=active_contracts_count,
        active_contracts_monthly_sum=active_contracts_monthly_sum,
    )
    _stats_cache[oid] = {"data": stats, "expires": time.monotonic() + _STATS_CACHE_TTL}
    return stats


def invalidate_stats_cache() -> None:
    """Invalidate the dashboard stats cache (call after invoice/contract mutations).
    Clears all per-user entries — each recomputes (owner-scoped) on next request."""
    _stats_cache.clear()
    _charts_cache.clear()


# "Rausgegangene" Rechnungen für den gestrichelten Zähl-Balken:
# alles, was an Kunden gestellt wurde — unabhängig vom Bezahlt-Status.
_ISSUED_STATUSES = [InvoiceStatus.gestellt, InvoiceStatus.bezahlt, InvoiceStatus.ueberfaellig]


@router.get("/charts")
async def get_chart_data(
    period: str = Query("30d", regex="^(30d|12m)$"),
    include_drafts: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cache_key = (current_owner_id.get(), period, include_drafts)
    entry = _charts_cache.get(cache_key)
    if entry is not None and time.monotonic() < entry["expires"]:
        return entry["data"]
    today = date.today()

    # --- Revenue data ---
    if period == "30d":
        # Daily for last 30 days
        start_date = today - relativedelta(days=29)
        statuses = [InvoiceStatus.bezahlt]
        if include_drafts:
            # Erwarteter Umsatz: auch gestellte/überfällige (sicherer als
            # Entwürfe!) und Entwürfe einbeziehen — nicht nur bezahlt+entwurf.
            statuses += [InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig, InvoiceStatus.entwurf]

        rev_result = await db.execute(
            select(
                Invoice.invoice_date,
                func.coalesce(func.sum(Invoice.total), 0),
                func.count(Invoice.id),
                func.min(Customer.name),  # bei genau 1 Rechnung = deren Kunde
                func.sum(case((Invoice.status == InvoiceStatus.bezahlt, 1), else_=0)),
                func.sum(case((Invoice.status.in_([InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig]), 1), else_=0)),
                func.sum(case((Invoice.status == InvoiceStatus.entwurf, 1), else_=0)),
            )
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(Invoice.status.in_(statuses), Invoice.invoice_date >= start_date)
            .group_by(Invoice.invoice_date)
        )
        rev_map: dict[str, dict] = {}
        for d, total, cnt, cust, paid_c, open_c, draft_c in rev_result.all():
            rev_map[d.isoformat()] = {
                "revenue": float(total), "count": int(cnt), "customer": cust,
                "paid": int(paid_c or 0), "open": int(open_c or 0), "draft": int(draft_c or 0),
            }

        # Gestellte Rechnungen (rausgegangen: gestellt/bezahlt/überfällig) —
        # bewusst unabhängig vom include_drafts-Toggle (Fakturierungs-Aktivität)
        issued_result = await db.execute(
            select(Invoice.invoice_date, func.count(Invoice.id))
            .where(
                Invoice.status.in_(_ISSUED_STATUSES),
                Invoice.invoice_date >= start_date,
            )
            .group_by(Invoice.invoice_date)
        )
        issued_map = {d.isoformat(): int(cnt) for d, cnt in issued_result.all()}

        exp_result = await db.execute(
            select(
                Expense.date,
                func.coalesce(func.sum(Expense.amount), 0),
            )
            .where(Expense.date >= start_date)
            .group_by(Expense.date)
        )
        exp_map: dict[str, float] = {}
        for d, total in exp_result.all():
            exp_map[d.isoformat()] = float(total)

        revenue_by_period = []
        for i in range(30):
            d = start_date + relativedelta(days=i)
            key = d.isoformat()
            rev = rev_map.get(key, {"revenue": 0.0, "count": 0, "customer": None, "paid": 0, "open": 0, "draft": 0})
            revenue_by_period.append({
                "label": d.strftime("%d.%m."),
                "revenue": rev["revenue"],
                "expenses": exp_map.get(key, 0.0),
                "invoice_count": rev["count"],
                "customer_name": rev["customer"] if rev["count"] == 1 else None,
                "issued_count": issued_map.get(key, 0),
                "paid_count": rev["paid"],
                "open_count": rev["open"],
                "draft_count": rev["draft"],
            })
    else:
        # Monthly for last 12 months (original logic)
        twelve_months_ago = today.replace(day=1) - relativedelta(months=11)
        statuses = [InvoiceStatus.bezahlt]
        if include_drafts:
            # Erwarteter Umsatz: auch gestellte/überfällige (sicherer als
            # Entwürfe!) und Entwürfe einbeziehen — nicht nur bezahlt+entwurf.
            statuses += [InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig, InvoiceStatus.entwurf]

        rev_result = await db.execute(
            select(
                func.extract("year", Invoice.invoice_date).label("y"),
                func.extract("month", Invoice.invoice_date).label("m"),
                func.coalesce(func.sum(Invoice.total), 0),
                func.count(Invoice.id),
                func.min(Customer.name),  # bei genau 1 Rechnung = deren Kunde
                func.sum(case((Invoice.status == InvoiceStatus.bezahlt, 1), else_=0)),
                func.sum(case((Invoice.status.in_([InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig]), 1), else_=0)),
                func.sum(case((Invoice.status == InvoiceStatus.entwurf, 1), else_=0)),
            )
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(
                Invoice.status.in_(statuses),
                Invoice.invoice_date >= twelve_months_ago,
            )
            .group_by("y", "m")
        )
        rev_map: dict[str, dict] = {}
        for y, m, total, cnt, cust, paid_c, open_c, draft_c in rev_result.all():
            key = f"{int(y)}-{int(m):02d}"
            rev_map[key] = {
                "revenue": float(total), "count": int(cnt), "customer": cust,
                "paid": int(paid_c or 0), "open": int(open_c or 0), "draft": int(draft_c or 0),
            }

        issued_result = await db.execute(
            select(
                func.extract("year", Invoice.invoice_date).label("y"),
                func.extract("month", Invoice.invoice_date).label("m"),
                func.count(Invoice.id),
            )
            .where(
                Invoice.status.in_(_ISSUED_STATUSES),
                Invoice.invoice_date >= twelve_months_ago,
            )
            .group_by("y", "m")
        )
        issued_map = {f"{int(y)}-{int(m):02d}": int(cnt) for y, m, cnt in issued_result.all()}

        exp_result = await db.execute(
            select(
                func.extract("year", Expense.date).label("y"),
                func.extract("month", Expense.date).label("m"),
                func.coalesce(func.sum(Expense.amount), 0),
            )
            .where(Expense.date >= twelve_months_ago)
            .group_by("y", "m")
        )
        exp_map: dict[str, float] = {}
        for y, m, total in exp_result.all():
            key = f"{int(y)}-{int(m):02d}"
            exp_map[key] = float(total)

        months_de = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        revenue_by_period = []
        for i in range(12):
            d = today.replace(day=1) - relativedelta(months=11 - i)
            key = f"{d.year}-{d.month:02d}"
            rev = rev_map.get(key, {"revenue": 0.0, "count": 0, "customer": None, "paid": 0, "open": 0, "draft": 0})
            revenue_by_period.append({
                "label": f"{months_de[d.month - 1]} {str(d.year)[2:]}",
                "revenue": rev["revenue"],
                "expenses": exp_map.get(key, 0.0),
                "invoice_count": rev["count"],
                "customer_name": rev["customer"] if rev["count"] == 1 else None,
                "issued_count": issued_map.get(key, 0),
                "paid_count": rev["paid"],
                "open_count": rev["open"],
                "draft_count": rev["draft"],
            })

    # --- invoice_status_distribution ---
    status_result = await db.execute(
        select(
            Invoice.status,
            func.count().label("cnt"),
            func.coalesce(func.sum(Invoice.total), 0).label("total"),
        ).group_by(Invoice.status)
    )
    invoice_status_distribution = [
        {"status": row[0].value, "count": row[1], "total": float(row[2])}
        for row in status_result.all()
    ]

    # --- top_customers: top 5 by paid invoice revenue ---
    top_result = await db.execute(
        select(
            Customer.name,
            func.sum(Invoice.total).label("revenue"),
            func.count(Invoice.id).label("invoices_count"),
        )
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.status == InvoiceStatus.bezahlt)
        .group_by(Customer.id, Customer.name)
        .order_by(desc("revenue"))
        .limit(5)
    )
    top_customers = [
        {
            "name": row[0],
            "revenue": float(row[1]),
            "invoices_count": row[2],
        }
        for row in top_result.all()
    ]

    # --- recent_invoices: last 5 ---
    inv_result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .order_by(desc(Invoice.created_at))
        .limit(5)
    )
    recent_invoices = [
        {
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer.name if inv.customer else "",
            "total": float(inv.total),
            "status": inv.status.value,
            "date": inv.invoice_date.isoformat(),
        }
        for inv in inv_result.scalars().unique().all()
    ]

    # --- recent_activities: last 10 ---
    act_result = await db.execute(
        select(Activity)
        .options(joinedload(Activity.customer))
        .order_by(desc(Activity.created_at))
        .limit(10)
    )
    recent_activities = [
        {
            "type": act.type,
            "title": act.title,
            "customer_name": act.customer.name if act.customer else "",
            "created_at": act.created_at.isoformat() if act.created_at else None,
        }
        for act in act_result.scalars().unique().all()
    ]

    result = {
        "revenue_by_period": revenue_by_period,
        "invoice_status_distribution": invoice_status_distribution,
        "top_customers": top_customers,
        "recent_invoices": recent_invoices,
        "recent_activities": recent_activities,
    }
    _charts_cache[cache_key] = {"data": result, "expires": time.monotonic() + _STATS_CACHE_TTL}
    return result


@router.get("/profitability", response_model=list[CustomerProfitability])
async def get_profitability(
    db: AsyncSession = Depends(get_db),
) -> list[CustomerProfitability]:
    # Revenue per customer (paid invoices)
    rev_result = await db.execute(
        select(
            Customer.id,
            Customer.name,
            func.coalesce(func.sum(Invoice.total), 0).label("revenue"),
            func.count(Invoice.id).label("invoices_count"),
        )
        .outerjoin(Invoice, (Invoice.customer_id == Customer.id) & (Invoice.status == InvoiceStatus.bezahlt))
        .group_by(Customer.id, Customer.name)
    )
    customer_data: dict[str, dict] = {}
    for row in rev_result.all():
        cid = str(row[0])
        customer_data[cid] = {
            "customer_id": cid,
            "customer_name": row[1],
            "revenue": float(row[2]),
            "invoices_count": row[3],
        }

    # Hours per customer (time entries)
    hours_result = await db.execute(
        select(
            TimeEntry.customer_id,
            func.coalesce(func.sum(TimeEntry.hours), 0).label("hours"),
        ).group_by(TimeEntry.customer_id)
    )
    for row in hours_result.all():
        cid = str(row[0])
        if cid in customer_data:
            customer_data[cid]["hours_logged"] = float(row[1])

    results = []
    for data in customer_data.values():
        revenue = data["revenue"]
        hours = data.get("hours_logged", 0.0)
        expenses = 0.0
        profit = revenue - expenses
        effective_rate = round(revenue / hours, 2) if hours > 0 else 0.0
        results.append(
            CustomerProfitability(
                customer_id=data["customer_id"],
                customer_name=data["customer_name"],
                revenue=revenue,
                expenses=expenses,
                hours_logged=hours,
                ai_hours=0.0,
                invoices_count=data["invoices_count"],
                effective_hourly_rate=effective_rate,
                profit=profit,
            )
        )

    results.sort(key=lambda x: x.revenue, reverse=True)
    return results


@router.get("/forecast", response_model=ForecastData)
async def get_forecast(
    db: AsyncSession = Depends(get_db),
) -> ForecastData:
    # Monthly recurring from active contracts
    result = await db.execute(
        select(func.coalesce(func.sum(Contract.monthly_amount), 0)).where(
            Contract.status == ContractStatus.aktiv
        )
    )
    monthly_recurring = float(result.scalar_one())
    annual_recurring = monthly_recurring * 12

    # Pipeline: orders with status=angebot
    result = await db.execute(
        select(
            func.coalesce(func.sum(Order.amount), 0),
            func.count(Order.id),
        ).where(Order.status == OrderStatus.angebot)
    )
    row = result.one()
    pipeline_value = float(row[0])
    pipeline_count = row[1]

    # Forecast calculations
    forecast_3m = monthly_recurring * 3 + pipeline_value * 0.3
    forecast_6m = monthly_recurring * 6 + pipeline_value * 0.5
    forecast_12m = monthly_recurring * 12 + pipeline_value * 0.7

    # Leads count (neu or kontaktiert)
    result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.status.in_([LeadStatus.neu, LeadStatus.kontaktiert])
        )
    )
    leads_count = result.scalar_one()

    return ForecastData(
        monthly_recurring=round(monthly_recurring, 2),
        annual_recurring=round(annual_recurring, 2),
        pipeline_value=round(pipeline_value, 2),
        pipeline_count=pipeline_count,
        forecast_3m=round(forecast_3m, 2),
        forecast_6m=round(forecast_6m, 2),
        forecast_12m=round(forecast_12m, 2),
        leads_count=leads_count,
    )


GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}

STATUS_LABELS = {
    "entwurf": "Entwurf",
    "gestellt": "Gestellt",
    "bezahlt": "Bezahlt",
    "ueberfaellig": "Überfällig",
    "storniert": "Storniert",
}


@router.get("/monthly-report")
async def generate_monthly_report(
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # --- KPIs ---

    _rs, _re = _month_bounds(year, month)

    # Revenue: paid invoices in this month
    result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == InvoiceStatus.bezahlt,
            Invoice.invoice_date >= _rs,
            Invoice.invoice_date < _re,
        )
    )
    revenue = float(result.scalar_one())

    # Expenses this month
    result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.date >= first_day,
            Expense.date <= last_day,
        )
    )
    expenses = float(result.scalar_one())

    profit = revenue - expenses

    # New customers this month
    result = await db.execute(
        select(func.count(Customer.id)).where(
            Customer.created_at >= _rs,
            Customer.created_at < _re,
        )
    )
    new_customers = result.scalar_one()

    # Completed orders this month
    result = await db.execute(
        select(Order)
        .options(joinedload(Order.customer))
        .where(
            Order.status == OrderStatus.abgeschlossen,
            Order.updated_at >= _rs,
            Order.updated_at < _re,
        )
    )
    completed_orders_raw = result.scalars().unique().all()
    completed_orders = [
        {
            "title": o.title,
            "customer_name": o.customer.name if o.customer else "",
            "amount": float(o.amount) if o.amount else None,
        }
        for o in completed_orders_raw
    ]

    kpis = {
        "revenue": revenue,
        "expenses": expenses,
        "profit": profit,
        "new_customers": new_customers,
    }

    # --- Invoices created/paid this month ---
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(
            Invoice.invoice_date >= first_day,
            Invoice.invoice_date <= last_day,
        )
        .order_by(Invoice.invoice_date)
    )
    invoices_raw = result.scalars().unique().all()
    invoices = [
        {
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer.name if inv.customer else "",
            "title": inv.title,
            "status": inv.status.value,
            "status_label": STATUS_LABELS.get(inv.status.value, inv.status.value),
            "total": float(inv.total),
            "date": inv.invoice_date.strftime("%d.%m.%Y"),
        }
        for inv in invoices_raw
    ]

    # --- Open invoices (gestellt or ueberfaellig) ---
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(
            Invoice.status.in_([InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig]),
        )
        .order_by(Invoice.due_date)
    )
    open_invoices_raw = result.scalars().unique().all()
    open_invoices = [
        {
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer.name if inv.customer else "",
            "total": float(inv.total),
            "due_date": inv.due_date.strftime("%d.%m.%Y") if inv.due_date else "",
            "status": inv.status.value,
            "status_label": STATUS_LABELS.get(inv.status.value, inv.status.value),
        }
        for inv in open_invoices_raw
    ]
    open_invoices_total = sum(i["total"] for i in open_invoices)

    # --- Time entries this month ---
    result = await db.execute(
        select(
            Customer.name,
            func.coalesce(func.sum(TimeEntry.hours), 0).label("hours"),
        )
        .join(Customer, TimeEntry.customer_id == Customer.id)
        .where(
            TimeEntry.date >= first_day,
            TimeEntry.date <= last_day,
        )
        .group_by(Customer.id, Customer.name)
        .order_by(desc("hours"))
    )
    time_entries_by_customer = [
        {"customer_name": row[0], "hours": float(row[1])}
        for row in result.all()
    ]
    total_hours = sum(e["hours"] for e in time_entries_by_customer)

    # --- Render PDF ---
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("monthly_report.html")

    month_name = GERMAN_MONTHS.get(month, str(month))

    html_content = template.render(
        settings=settings,
        year=year,
        month=month,
        month_name=month_name,
        kpis=kpis,
        invoices=invoices,
        open_invoices=open_invoices,
        open_invoices_total=open_invoices_total,
        time_entries_by_customer=time_entries_by_customer,
        total_hours=total_hours,
        completed_orders=completed_orders,
    )

    pdf_bytes = await asyncio.to_thread(lambda: HTML(string=html_content).write_pdf())

    filename = download_name("Monatsbericht", f"{year}-{month:02d}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
