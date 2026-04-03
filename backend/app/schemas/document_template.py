import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    description: str | None = None
    content: str
    is_system: bool
    created_at: datetime


class GenerateRequest(BaseModel):
    template_id: uuid.UUID
    customer_id: uuid.UUID
