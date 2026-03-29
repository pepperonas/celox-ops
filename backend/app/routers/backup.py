import base64
import json
import os
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

from app.auth import get_current_user
from app.database import get_db
from app.models.customer import Base

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

    # Auto-discover all tables from SQLAlchemy Base
    for mapper in Base.registry.mappers:
        model = mapper.class_
        table_name = model.__tablename__
        result = await db.execute(select(model))
        rows = result.scalars().all()
        data[table_name] = [_row_to_dict(r) for r in rows]

    # Collect PDFs as base64
    pdfs = {}
    pdf_dir = settings.PDF_STORAGE_PATH
    if os.path.isdir(pdf_dir):
        for filename in os.listdir(pdf_dir):
            if filename.endswith(".pdf"):
                filepath = os.path.join(pdf_dir, filename)
                with open(filepath, "rb") as f:
                    pdfs[filename] = base64.b64encode(f.read()).decode("utf-8")
    data["pdfs"] = pdfs

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    json_str = json.dumps(data, default=_serialize, ensure_ascii=False, indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="celox-ops-backup-{timestamp}.json"'
        },
    )
