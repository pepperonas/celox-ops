import json
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order
from app.models.contract import Contract
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.time_entry import TimeEntry
from app.models.expense import Expense
from app.models.activity import Activity

router = APIRouter(
    prefix="/api/backup",
    tags=["backup"],
    dependencies=[Depends(get_current_user)],
)


def _serialize(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "value") and isinstance(obj.value, str):  # Enum
        return obj.value
    if hasattr(obj, "hex"):  # UUID (including asyncpg UUID)
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def _row_to_dict(row) -> dict:
    d = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        d[col.name] = val
    return d


@router.get("/export")
async def export_database(db: AsyncSession = Depends(get_db)) -> Response:
    """Exportiert die gesamte Datenbank als JSON."""
    data = {}

    for model, name in [
        (Customer, "customers"),
        (Order, "orders"),
        (Contract, "contracts"),
        (Invoice, "invoices"),
        (Lead, "leads"),
        (TimeEntry, "time_entries"),
        (Expense, "expenses"),
        (Activity, "activities"),
    ]:
        result = await db.execute(select(model))
        rows = result.scalars().all()
        data[name] = [_row_to_dict(r) for r in rows]

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    json_str = json.dumps(data, default=_serialize, ensure_ascii=False, indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="celox-ops-backup-{timestamp}.json"'
        },
    )
