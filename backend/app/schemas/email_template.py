import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailTemplateBase(BaseModel):
    name: str
    subject: str
    body: str
    category: str  # rechnung, angebot, mahnung, akquise, allgemein


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body: str | None = None
    category: str | None = None


class EmailTemplateResponse(EmailTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
