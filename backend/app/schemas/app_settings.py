from pydantic import BaseModel, Field


class AppSettingsResponse(BaseModel):
    default_unit_price: float
    invoice_prefix: str
    # Google Places (Lead-Suche): der Key wird NIE im Klartext zurückgegeben.
    google_places_configured: bool = False
    google_places_key_hint: str | None = None  # z. B. "••••Ab12"
    google_places_calls_this_month: int = 0
    # KI-Lead-Suche
    ai_model: str = "claude-sonnet-5"
    ai_monthly_budget_eur: float = 20.0


class AppSettingsUpdate(BaseModel):
    default_unit_price: float | None = Field(default=None, ge=0)
    invoice_prefix: str | None = Field(default=None, min_length=1, max_length=10)
    # "" = Key entfernen; None = unverändert; sonst neuer Key.
    google_places_api_key: str | None = Field(default=None, max_length=255)
    ai_model: str | None = Field(default=None, max_length=40)
    ai_monthly_budget_eur: float | None = Field(default=None, ge=0)
