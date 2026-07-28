"""Modellwahl, Monatsverbrauch und Budget-Stand der KI-Funktionen.

Vorher lag das privat im Rainmaker-Router (`_budget_status`,
`_ai_month_spent_eur`). Mit der zweiten Stelle, die es braucht (KI-To-dos am
Kunden), wäre daraus eine Kopie geworden — und eine Kopie der Budget-Regel ist
genau die Art Duplikat, die irgendwann auseinanderläuft und dann Geld kostet.

Alles hier ist owner-scoped über die Tenancy-Events: `AiLeadRun` und
`AppSettings` sind eigene Entitäten, die Abfragen filtern also automatisch auf
den Arbeitsbereich.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_lead_run import AiLeadRun
from app.schemas.rainmaker import AiBudget
from app.services.ai_pricing import ALLOWED_MODELS, DEFAULT_MODEL

# Rückfall, wenn ein Arbeitsbereich noch keine Einstellungen hat.
DEFAULT_BUDGET_EUR = 20.0


def month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def month_spent_eur(db: AsyncSession) -> float:
    """EUR-Verbrauch der KI-Läufe im laufenden Monat."""
    total = (await db.execute(
        select(func.coalesce(func.sum(AiLeadRun.cost_eur), 0))
        .where(AiLeadRun.created_at >= month_start())
    )).scalar_one()
    return float(total or 0)


def budget_status(spent_eur: float, budget_eur: float) -> AiBudget:
    return AiBudget(
        budget_eur=round(budget_eur, 2), spent_eur=round(spent_eur, 4),
        remaining_eur=round(max(0.0, budget_eur - spent_eur), 4),
        warn=budget_eur > 0 and spent_eur >= 0.8 * budget_eur,
    )


def resolve_model(app_row) -> str:
    """Eingestelltes Modell, auf die bekannten Modelle geklemmt."""
    model = getattr(app_row, "ai_model", None) or DEFAULT_MODEL
    return model if model in ALLOWED_MODELS else DEFAULT_MODEL


def resolve_budget_eur(app_row) -> float:
    value = getattr(app_row, "ai_monthly_budget_eur", None)
    return float(value) if value is not None else DEFAULT_BUDGET_EUR


async def ai_context(db: AsyncSession) -> tuple[str, float, float]:
    """(Modell, Monatsbudget, bisher verbraucht) für diesen Arbeitsbereich."""
    from app.models.app_settings import AppSettings

    app_row = (await db.execute(select(AppSettings).limit(1))).scalar_one_or_none()
    return resolve_model(app_row), resolve_budget_eur(app_row), await month_spent_eur(db)


__all__ = [
    "DEFAULT_BUDGET_EUR", "ai_context", "budget_status", "month_spent_eur",
    "month_start", "resolve_budget_eur", "resolve_model",
]
