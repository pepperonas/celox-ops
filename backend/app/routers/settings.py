from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.app_settings import AppSettings
from app.schemas.app_settings import AppSettingsResponse, AppSettingsUpdate
from app.services.places_usage import calls_this_month, mask_key

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


def _to_response(row: AppSettings) -> AppSettingsResponse:
    key = row.google_places_api_key
    return AppSettingsResponse(
        default_unit_price=float(row.default_unit_price),
        invoice_prefix=row.invoice_prefix,
        google_places_configured=bool(key),
        google_places_key_hint=mask_key(key),
        google_places_calls_this_month=calls_this_month(row.google_places_period, row.google_places_calls),
        ai_model=row.ai_model,
        ai_monthly_budget_eur=float(row.ai_monthly_budget_eur),
    )


@router.get("", response_model=AppSettingsResponse)
async def read_settings(db: AsyncSession = Depends(get_db)) -> AppSettingsResponse:
    return _to_response(await get_or_create_settings(db))


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
    if data.google_places_api_key is not None:
        # "" entfernt den Key, sonst setzen (getrimmt).
        row.google_places_api_key = data.google_places_api_key.strip() or None
    if data.ai_model is not None:
        from app.services.ai_pricing import ALLOWED_MODELS, DEFAULT_MODEL
        row.ai_model = data.ai_model if data.ai_model in ALLOWED_MODELS else DEFAULT_MODEL
    if data.ai_monthly_budget_eur is not None:
        row.ai_monthly_budget_eur = data.ai_monthly_budget_eur
    await db.flush()
    return _to_response(row)
