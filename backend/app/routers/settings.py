from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.app_settings import AppSettings
from app.schemas.app_settings import AppSettingsResponse, AppSettingsUpdate

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)


async def get_or_create_settings(db: AsyncSession) -> AppSettings:
    row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    if row is None:
        row = AppSettings()
        db.add(row)
        await db.flush()
    return row


@router.get("", response_model=AppSettingsResponse)
async def read_settings(db: AsyncSession = Depends(get_db)) -> AppSettingsResponse:
    row = await get_or_create_settings(db)
    return AppSettingsResponse.model_validate(row)


@router.put("", response_model=AppSettingsResponse)
async def update_settings(
    data: AppSettingsUpdate, db: AsyncSession = Depends(get_db)
) -> AppSettingsResponse:
    row = await get_or_create_settings(db)
    if data.default_unit_price is not None:
        row.default_unit_price = data.default_unit_price
    if data.invoice_prefix is not None:
        # Sanitize: uppercase alphanumerics only (used verbatim in invoice numbers).
        import re
        clean = re.sub(r"[^A-Za-z0-9]", "", data.invoice_prefix).upper()[:10]
        if clean:
            row.invoice_prefix = clean
    await db.flush()
    return AppSettingsResponse.model_validate(row)
