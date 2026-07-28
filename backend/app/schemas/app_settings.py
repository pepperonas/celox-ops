from pydantic import BaseModel, Field


class AppSettingsResponse(BaseModel):
    default_unit_price: float
    invoice_prefix: str
    # Google Places (Lead-Suche): der Key wird NIE im Klartext zurückgegeben.
    google_places_configured: bool = False
    google_places_key_hint: str | None = None  # z. B. "••••Ab12"
    google_places_calls_this_month: int = 0
    # Hostinger (Kostenimport) — Schlüssel nie im Klartext.
    hostinger_configured: bool = False
    hostinger_key_hint: str | None = None
    # KI-Zugang: der Schlüssel wird NIE im Klartext zurückgegeben.
    ai_key_configured: bool = False
    ai_key_hint: str | None = None        # z. B. "••••Ab12"
    # KI-Lead-Suche
    ai_model: str = "claude-sonnet-5"
    ai_monthly_budget_eur: float = 20.0
    # Automatische (kostenlose) Website-Analyse nach dem Lead-Import
    auto_analyze_websites: bool = True


class AppSettingsUpdate(BaseModel):
    default_unit_price: float | None = Field(default=None, ge=0)
    invoice_prefix: str | None = Field(default=None, min_length=1, max_length=10)
    # "" = Key entfernen; None = unverändert; sonst neuer Key.
    google_places_api_key: str | None = Field(default=None, max_length=255)
    # "" = Schlüssel entfernen; None = unverändert; sonst neuer Schlüssel.
    anthropic_api_key: str | None = Field(default=None, max_length=255)
    hostinger_api_key: str | None = Field(default=None, max_length=255)
    ai_model: str | None = Field(default=None, max_length=40)
    ai_monthly_budget_eur: float | None = Field(default=None, ge=0)
    auto_analyze_websites: bool | None = None
