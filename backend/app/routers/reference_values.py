"""Verwaltung feldbezogener Referenzwerte/Tags (Phase B2).

GET  /api/reference-values/fields          → verwaltbare Felder + Label
GET  /api/reference-values?field=&q=       → Werte mit Verwendungszähler + Quelle
POST /api/reference-values                 → eigenen Wert anlegen
POST /api/reference-values/rename          → umbenennen + global propagieren
DELETE /api/reference-values               → löschen (optional ersetzen)

Owner-scoped (Tenancy). Destruktive Ops (rename/delete) sind für die Rolle
`mitarbeiter` gesperrt: DELETE via Middleware automatisch, rename über die
Denylist in `middleware/permissions.py`.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.services import reference_data as rd

router = APIRouter(
    prefix="/api/reference-values",
    tags=["reference-values"],
    dependencies=[Depends(get_current_user)],
)


def _check_field(field: str) -> None:
    if field not in rd.MANAGED_FIELDS:
        raise HTTPException(status_code=422, detail=f"Unverwaltbares Feld '{field}'.")


class CreateBody(BaseModel):
    field: str
    value: str


class RenameBody(BaseModel):
    field: str
    old: str
    new: str


class DeleteBody(BaseModel):
    field: str
    value: str
    replace_with: str | None = None


@router.get("/fields")
async def list_fields() -> dict:
    return {"fields": [{"key": k, "label": v} for k, v in rd.FIELD_LABELS.items()]}


@router.get("")
async def list_values(
    field: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _check_field(field)
    return {"field": field, "values": await rd.list_values(field, db)}


@router.post("")
async def create_value(body: CreateBody, db: AsyncSession = Depends(get_db)) -> dict:
    _check_field(body.field)
    try:
        value = await rd.create_value(body.field, body.value, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"value": value}


@router.post("/rename")
async def rename_value(body: RenameBody, db: AsyncSession = Depends(get_db)) -> dict:
    _check_field(body.field)
    try:
        return await rd.rename_value(body.field, body.old, body.new, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("")
async def delete_value(body: DeleteBody, db: AsyncSession = Depends(get_db)) -> dict:
    _check_field(body.field)
    try:
        return await rd.delete_value(body.field, body.value, db, replace_with=body.replace_with)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
