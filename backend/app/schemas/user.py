import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    google_email: str | None = None
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = None
    google_email: str | None = None
    role: str = "user"


class UserUpdate(BaseModel):
    email: str | None = None
    # "" = Verknüpfung entfernen; None = Feld nicht ändern
    google_email: str | None = None
    role: str | None = None
    is_active: bool | None = None


class PasswordSet(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
