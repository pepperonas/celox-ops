import uuid
from datetime import date as DateType
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.expense import ExpenseCategory


class ExpenseBase(BaseModel):
    description: str
    category: ExpenseCategory
    amount: Decimal
    date: DateType
    vendor: str | None = None
    recurring: bool = False
    notes: str | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    description: str | None = None
    category: ExpenseCategory | None = None
    amount: Decimal | None = None
    date: DateType | None = None
    vendor: str | None = None
    recurring: bool | None = None
    notes: str | None = None


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


# --------------------------------------------------------------------------- #
#  Hostinger-Kostenimport
# --------------------------------------------------------------------------- #
class HostingerDraft(BaseModel):
    """Ein Ausgaben-Entwurf aus einem Hostinger-Abo. `duplicate` setzt der Server."""
    description: str
    category: ExpenseCategory
    amount: Decimal
    date: DateType
    vendor: str | None = None
    recurring: bool = True
    notes: str | None = None
    external_ref: str
    subscription_id: str | None = None
    duplicate: bool = False


class HostingerPreview(BaseModel):
    drafts: list[HostingerDraft] = []
    skipped: list[str] = []
    total: Decimal = Decimal("0")
    counts: dict[str, int] = {}
    already_imported: int = 0


class HostingerImportRequest(BaseModel):
    refs: list[str] = []          # Auswahl über external_ref


class HostingerImportResult(BaseModel):
    created: int = 0
    skipped_duplicates: int = 0
    total: Decimal = Decimal("0")
    expense_ids: list[uuid.UUID] = []
