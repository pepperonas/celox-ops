import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PagespeedResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    url: str
    strategy: str
    score_performance: float | None = None
    score_accessibility: float | None = None
    score_best_practices: float | None = None
    score_seo: float | None = None
    pdf_path: str | None = None
    created_at: datetime
