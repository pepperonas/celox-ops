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
    # Palette-Schlüssel, nicht Farbwert (s. Modell). None = neutral.
    color: str | None = None
    # Reihenfolge innerhalb der Favoriten (kanalübergreifend, s. Modell).
    favorite_order: int | None = None


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
    color: str | None = None
    favorite_order: int | None = None


class OutreachTemplateResponse(OutreachTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usage_count: int
    created_at: datetime
    updated_at: datetime


class OutreachReorder(BaseModel):
    """Neue Reihenfolge eines Kanals als vollständige ID-Liste.

    Bewusst die ganze Liste und nicht „verschiebe X hinter Y": Der Client kennt
    die Zielordnung ohnehin, und ein Bulk-Setzen ist atomar. Einzelne PUTs pro
    Karte wären N Requests und könnten zur Hälfte scheitern.
    """

    channel: OutreachChannel
    ids: list[uuid.UUID]


class OutreachFavoriteReorder(BaseModel):
    """Neue Reihenfolge der Favoriten als vollständige ID-Liste.

    Ohne `channel`: Die Favoriten-Sektion ist kanalübergreifend. Sie schreibt
    `favorite_order`, nicht `sort_order` — sonst würde ein Zug in den Favoriten
    die Reihenfolge der Kanal-Listen mitverändern.
    """

    ids: list[uuid.UUID]
