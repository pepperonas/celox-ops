import uuid
from datetime import date as DateType
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.rainmaker import AiBudget, AiRunCost


class CustomerBase(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    website: str | None = None
    token_tracker_url: str | None = None
    github_repos: str | None = None
    notes: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    website: str | None = None
    token_tracker_url: str | None = None
    github_repos: str | None = None
    notes: str | None = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CustomerDetail(CustomerResponse):
    orders_count: int = 0
    contracts_count: int = 0
    invoices_count: int = 0


# --------------------------------------------------------------------------- #
#  KI-Vorschläge für To-dos zu diesem Kunden
# --------------------------------------------------------------------------- #
class TodoSuggestion(BaseModel):
    """Ein Vorschlag — noch nichts angelegt.

    `evidence` ist das wörtliche Zitat aus den Kundendaten, auf das sich der
    Vorschlag stützt; ohne Beleg wird ein Vorschlag serverseitig verworfen.
    `duplicate` markiert Titel, die schon als offenes To-do existieren.
    """
    title: str
    notes: str | None = None
    priority: str = "normal"
    due_date: DateType | None = None
    evidence: str = ""
    duplicate: bool = False


class TodoSuggestionResponse(BaseModel):
    suggestions: list[TodoSuggestion] = []
    # Was die KI bewusst nicht übernommen hat bzw. was der Server verworfen hat —
    # sichtbar, damit nichts still verschwindet.
    ignored: list[str] = []
    cached: bool = False
    run: AiRunCost
    budget: AiBudget
