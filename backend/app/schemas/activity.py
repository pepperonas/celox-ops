import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityCreate(BaseModel):
    customer_id: uuid.UUID
    type: str  # note, call, email, meeting, invoice, order, contract
    title: str
    description: str | None = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    type: str
    title: str
    description: str | None = None
    created_at: datetime
