"""Schemas des Marktradars."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.market_product import MarketStatus


class MarketProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    catalog_id: str
    produkt: str
    hersteller: str
    vendor: str
    vendor_slug: str
    konzern: str | None = None
    kategorie: str

    ref_url: str
    ref_status: str
    url_ok: bool
    url_geprueft: str | None = None
    refs: int
    kunden: str | None = None

    zielgruppe: str | None = None
    branchen: list[str] = []
    prozesse: list[str] = []
    nutzer: list[str] = []
    pains: list[str] = []
    ki: list[str] = []
    nutzen: str | None = None
    integration: str | None = None
    int_level: str
    notiz: str | None = None

    lead: int
    business: int
    prio: str
    dach: str | None = None
    score: int
    breakdown: list[dict] = []

    marketplace: bool
    mp_evidence: list[str] = []
    reg: list[str] = []
    self_compete: bool

    # Angereicherte Kontaktdaten. `contact_evidence` trägt Quelle + Zitat je Feld —
    # ohne Beleg wäre „korrekt" keine überprüfbare Aussage, deshalb geht der Beleg
    # mit an die Oberfläche und nicht nur in die Datenbank.
    website: str | None = None
    email: str | None = None
    email_status: str | None = None
    phone: str | None = None
    decision_maker: str | None = None
    employee_count: int | None = None
    contact_evidence: dict | None = None
    contact_checked_at: datetime | None = None

    status: MarketStatus
    ops_note: str | None = None
    rainmaker_lead_id: uuid.UUID | None = None
    pushed_at: datetime | None = None


class MarketProductUpdate(BaseModel):
    """Nur die Felder, die ops selbst besitzt — Katalogdaten sind hier read-only."""

    status: MarketStatus | None = None
    ops_note: str | None = None


class MarketBausteinResponse(BaseModel):
    """Baustein mit live gegen die gefilterte Produktmenge gerechneten Kennzahlen."""

    nr: int
    titel: str
    was: str | None = None
    warum: str | None = None
    vorsicht: str | None = None
    aufwand: str | None = None
    catalog_ids: list[str] = []
    treffer: int = 0
    reach: int = 0
    avg_score: int = 0
    kategorien: int = 0


class MarketStats(BaseModel):
    """Kennzahlen und Diagramm-Aggregate für die aktuell gefilterte Menge."""

    produkte: int
    prio_a: int
    verzeichnisse: int
    hersteller: int
    kategorien: int
    referenzen: int
    marketplace: int
    regulatorik: int
    integration_leicht: int
    offen: int
    in_pipeline: int
    avg_lead: float
    avg_business: float
    avg_score: int
    branchen: list[dict] = []
    kategorien_top: list[dict] = []
    reg_top: list[dict] = []
    lead_hist: list[dict] = []
    business_hist: list[dict] = []
    score_bins: list[dict] = []
    prio_bins: list[dict] = []
    int_bins: list[dict] = []
    status_bins: list[dict] = []


class MarketVendor(BaseModel):
    vendor: str
    vendor_slug: str
    konzern: str | None = None
    produkte: int
    refs: int
    avg_lead: float
    avg_score: int
    marketplace: bool
    kategorien: list[str] = []
    reg: list[str] = []
    catalog_ids: list[str] = []


class MarketCategory(BaseModel):
    kategorie: str
    produkte: int
    refs: int
    avg_score: int
    avg_business: float
    prio_a: int
    marketplace: int
    oeffentlich: int
    top: list[dict] = []
    prozesse: list[dict] = []
    risiken: list[dict] = []


class ToPipelineRequest(BaseModel):
    """Optionale Übersteuerung beim Übernehmen in die Pipeline."""

    force: bool = False
    priority: str | None = Field(default=None, pattern="^(low|medium|high)$")
    note: str | None = None


class ToPipelineResponse(BaseModel):
    lead_id: uuid.UUID
    company: str
    created: bool          # False = bestehender Lead wurde verknüpft
    duplicate_reason: str | None = None


class MarketImportResult(BaseModel):
    stand: str | None = None
    angelegt: int = 0
    aktualisiert: int = 0
    unveraendert: int = 0
    bausteine: int = 0
    verwaist: list[str] = []   # in ops vorhanden, im Katalog nicht mehr


# ---------------------------------------------------------- Referenzkunden


class MarketReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    company: str
    website: str | None = None
    source_url: str
    form: str
    status: str
    rainmaker_lead_id: uuid.UUID | None = None


class MarketReferenceItem(MarketReferenceResponse):
    """Mit Herstellerangaben und Bewertung — beides, damit die Liste ohne Nachladen
    lesbar UND sortierbar ist.

    `score_teile` geht bewusst mit an die Oberfläche: Eine Reihenfolge, deren Zustande-
    kommen man nicht sehen kann, ist im Vertrieb wertlos — man muss ihr widersprechen
    können (s. `services/market_reference_scoring.py`).
    """

    produkt: str | None = None
    hersteller: str | None = None
    kategorie: str | None = None
    score: int = 0
    score_teile: dict[str, int] = {}
    orgtyp: str = "unbekannt"
    systeme: int = 1
    baustein_nr: int | None = None
    baustein_titel: str | None = None


class MarketReferenceStats(BaseModel):
    """Kennzahlen der Kundensicht (nicht der Hersteller — die stehen in MarketStats)."""

    firmen: int
    firmen_distinkt: int
    mehrfachnutzer: int
    mit_baustein: int
    mit_website: int
    offen: int
    in_pipeline: int
    verworfen: int
    verzeichnisse: int
    orgtypen: list[dict] = []
    top_hersteller: list[dict] = []


class MarketReferenceListe(BaseModel):
    items: list[MarketReferenceItem]
    total: int
    page: int
    page_size: int
    pages: int


class MarketReferenceUpdate(BaseModel):
    status: str | None = None


class ReferencesToPipelineRequest(BaseModel):
    ids: list[uuid.UUID]
    force: bool = False


class ReferencesToPipelineResponse(BaseModel):
    created: list[dict]
    linked: list[dict]
    failed: list[dict]


class MarketReferenceSystem(BaseModel):
    """Ein System, das diese Firma einsetzt — mit der passenden Aufsatzlösung."""

    reference_id: uuid.UUID
    product_id: uuid.UUID
    produkt: str | None = None
    hersteller: str | None = None
    source_url: str
    baustein_nr: int | None = None
    baustein_titel: str | None = None


class MarketReferenceDetail(BaseModel):
    """Eine Firma in ganzer Tiefe — für die Detail-Seite.

    Enthält alles, was für die Ansprache gebraucht wird: welche Systeme mit Beleg,
    welche Bausteine passen, Kontaktdaten mit Herkunft, Score-Zerlegung. `contact_evidence`
    geht mit, damit jeder Wert am Bildschirm nachprüfbar ist statt nur behauptet.
    """

    company: str
    company_norm: str
    website: str | None = None
    website_source: str | None = None
    email: str | None = None
    email_status: str | None = None
    phone: str | None = None
    decision_maker: str | None = None
    employee_count: int | None = None
    address: str | None = None
    contact_evidence: dict | None = None
    contact_checked_at: datetime | None = None
    status: str
    score: int
    score_teile: dict[str, int] = {}
    orgtyp: str
    systeme: int
    reference_ids: list[uuid.UUID] = []
    rainmaker_lead_id: uuid.UUID | None = None
    produkte: list["MarketReferenceSystem"] = []
    bausteine: list[dict] = []


class MarketReferenceGroup(BaseModel):
    """EINE Firma mit allen ihren Systemen — die eigentliche Kundensicht.

    Die Tabelle speichert ein Paar (Firma, Hersteller); ungruppiert erschien eine Firma
    mit drei Systemen dreimal in der Liste und belegte die Spitze mehrfach. Für die
    Frage „welche Kunden lohnen sich" ist die Firma die Einheit, nicht das Paar.
    """

    company: str
    company_norm: str
    website: str | None = None
    status: str
    score: int
    score_teile: dict[str, int] = {}
    orgtyp: str
    systeme: int
    reference_ids: list[uuid.UUID] = []
    produkte: list[MarketReferenceSystem] = []
    # Angereichert? Die Liste zeigt es als Kennzeichen, ohne die Detailseite zu öffnen.
    email: str | None = None
    phone: str | None = None
    decision_maker: str | None = None


class MarketReferenceGroupListe(BaseModel):
    items: list[MarketReferenceGroup]
    total: int
    page: int
    page_size: int
    pages: int
