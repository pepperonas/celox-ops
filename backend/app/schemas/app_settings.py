from pydantic import BaseModel, ConfigDict, Field


class AppSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_unit_price: float
    invoice_prefix: str


class AppSettingsUpdate(BaseModel):
    default_unit_price: float | None = Field(default=None, ge=0)
    invoice_prefix: str | None = Field(default=None, min_length=1, max_length=10)
