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
    # Herkunftsschlüssel (z. B. „hostinger:<abo>:<datum>"). Beim normalen Anlegen
    # leer; wird gesetzt, wenn eine gelöschte importierte Ausgabe per „Rückgängig"
    # wiederhergestellt wird — sonst gälte ihr Zeitraum als nicht importiert und
    # der nächste Hostinger-Lauf würde sie ein zweites Mal buchen.
    external_ref: str | None = None


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
    # Nötig, damit die Liste beim Wiederherstellen einer gelöschten Ausgabe die
    # Herkunft mitgeben kann (siehe ExpenseCreate).
    external_ref: str | None = None


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
    # Zugeordnete Domain und woher sie kommt: `confirmed` = vom Nutzer bestätigt,
    # `same_order` = Sekunden nach dem Abo registriert, `sequence` = nur über die
    # Reihenfolge abgeleitet (prüfen), `unmatched` = keine gefunden.
    domain: str | None = None
    domain_confidence: str | None = None
    domain_delta_seconds: int | None = None
    domain_candidates: list[str] = []
    # Bei `duplicate`: die Beschreibung, die schon in der Buchung steht. Weicht sie
    # ab (z. B. noch „Domain .de"), kann sie nachgezogen werden.
    imported_description: str | None = None


class HostingerPreview(BaseModel):
    drafts: list[HostingerDraft] = []
    skipped: list[str] = []
    total: Decimal = Decimal("0")
    counts: dict[str, int] = {}
    already_imported: int = 0
    all_domains: list[str] = []   # zur Korrektur einer Zuordnung im Dialog


class HostingerImportRequest(BaseModel):
    refs: list[str] = []          # Auswahl über external_ref
    # Korrigierte Zuordnungen {subscription_id: domain}. Werden gegen das echte
    # Portfolio geprüft und für künftige Läufe gespeichert.
    domains: dict[str, str] = {}


class HostingerImportResult(BaseModel):
    created: int = 0
    skipped_duplicates: int = 0
    total: Decimal = Decimal("0")
    expense_ids: list[uuid.UUID] = []


class HostingerRelabelChange(BaseModel):
    external_ref: str
    before: str
    after: str


class HostingerRelabelResult(BaseModel):
    """Nachziehen von Beschreibung/Notiz bereits importierter Buchungen.

    Betrag, Datum und Kategorie bleiben unangetastet — nur der Text, damit eine
    Buchung „Domain .de" den inzwischen zugeordneten Namen bekommt.
    """
    updated: int = 0
    unchanged: int = 0
    changes: list[HostingerRelabelChange] = []
