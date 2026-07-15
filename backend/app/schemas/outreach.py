import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.outreach_template import OutreachCategory, OutreachChannel


class OutreachTemplateBase(BaseModel):
    channel: OutreachChannel
    category: OutreachCategory
    title: str
    subject: str | None = None
    body: str
    notes: str | None = None
    sort_order: int = 0
    is_favorite: bool = False


class OutreachTemplateCreate(OutreachTemplateBase):
    pass


class OutreachTemplateUpdate(BaseModel):
    channel: OutreachChannel | None = None
    category: OutreachCategory | None = None
    title: str | None = None
    subject: str | None = None
    body: str | None = None
    notes: str | None = None
    sort_order: int | None = None
    is_favorite: bool | None = None


class OutreachTemplateResponse(OutreachTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usage_count: int
    created_at: datetime
    updated_at: datetime
