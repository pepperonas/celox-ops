"""Anthropic-Zugang pro Arbeitsbereich auflösen.

**Warum nicht mehr global:** der Schlüssel lag als `ANTHROPIC_API_KEY` in der
`.env` und galt damit für alle. Ein zweiter Bereichs-Inhaber hätte über den
Schlüssel — und die Rechnung — des ersten abgefragt. Jeder Inhaber hinterlegt
deshalb seinen eigenen Schlüssel in den Einstellungen (`app_settings`, pro
Arbeitsbereich einzeilig).

**Mitarbeitende** haben bewusst keinen eigenen: sie arbeiten IM Bereich ihres
Inhabers, und `app_settings` wird über `workspace_owner_id` aufgelöst — sie nutzen
also automatisch den Schlüssel und das Budget des Bereichs. Ändern dürfen sie ihn
nicht (siehe `routers/settings.py`).

**Kein Rückfall auf die `.env` zur Laufzeit.** Ein stiller Rückfall würde
bedeuten, dass ein neuer Nutzer ohne eigenen Schlüssel auf Kosten des
`.env`-Inhabers abfragt. Fehlt der Schlüssel, gibt es einen klaren 503 mit
Verweis auf die Einstellungen. Die `.env`-Variable dient nur noch als Quelle für
die einmalige Übernahme (`scripts/adopt_env_anthropic_key.py`).
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MISSING_KEY_DETAIL = (
    "Für diesen Arbeitsbereich ist kein Anthropic-API-Key hinterlegt. "
    "Einstellungen → KI-Zugang → eigenen Schlüssel eintragen "
    "(console.anthropic.com). Abgerechnet wird über diesen Schlüssel."
)


async def resolve_anthropic_key(db: AsyncSession) -> str | None:
    """Schlüssel des aktuellen Arbeitsbereichs (owner-scoped) oder None."""
    from app.models.app_settings import AppSettings

    row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    key = (row.anthropic_api_key or "").strip() if row else ""
    return key or None


async def require_anthropic_key(db: AsyncSession) -> str:
    """Wie `resolve_anthropic_key`, aber mit 503 statt None."""
    key = await resolve_anthropic_key(db)
    if not key:
        raise HTTPException(status_code=503, detail=MISSING_KEY_DETAIL)
    return key
