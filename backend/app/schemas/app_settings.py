from pydantic import BaseModel, ConfigDict, Field


class AppSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_unit_price: float


class AppSettingsUpdate(BaseModel):
    default_unit_price: float | None = Field(default=None, ge=0)
