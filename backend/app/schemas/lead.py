import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    url: str
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    status: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    url: str | None = None
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    status: str | None = None


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
