"""Marktradar — Recherchekatalog als eigene Sektion, mit Übergabe in die Pipeline.

GET    /api/market/products              → gefilterte Trefferliste
GET    /api/market/stats                 → Kennzahlen + Diagramm-Aggregate (folgen dem Filter)
GET    /api/market/vendors               → Hersteller-Rollup
GET    /api/market/konzerne              → Eigentümer mit mehr als einem Produkt
GET    /api/market/categories            → Kategorie-Rollup inkl. Risiken
GET    /api/market/bausteine             → Lösungsbausteine mit Reichweite
GET    /api/market/facets                → Auswahlwerte für die Filter
PATCH  /api/market/products/{id}         → eigener Bearbeitungsstand (Status, Notiz)
POST   /api/market/products/{id}/to-pipeline → Hersteller als Rainmaker-Lead übernehmen

**Kein Import-Endpunkt.** Den Katalog einspielen ist Wartung, keine Funktion der
Anwendung — der Weg ist `python -m app.scripts.import_market_catalog` auf dem
Server. Ein HTTP-Upload hätte bedeutet, dass jede Rolle mit Radar-Zugriff
(auch `mitarbeiter`) alle 142 Einträge überschreiben kann; der Nutzen dafür war
eine Datei, die alle paar Wochen einmal wechselt. `services/market_import.py`
bleibt — es trägt das CLI-Skript und dessen Idempotenz-Tests.

Alle Endpunkte sind owner-scoped (Tenancy). Der Filter wird **einmal** in
`_filtered()` angewandt und von allen Aggregaten wiederverwendet — sonst driften
Diagramm und Liste auseinander.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.market_baustein import MarketBaustein
from app.models.market_product import MarketProduct, MarketStatus
from app.schemas.market import (
    MarketBausteinResponse,
    MarketCategory,
    MarketProductResponse,
    MarketProductUpdate,
    MarketStats,
    MarketVendor,
    ToPipelineRequest,
    ToPipelineResponse,
)
from app.services import market_catalog as agg
from app.services.market_pipeline import to_pipeline

router = APIRouter(
    prefix="/api/market",
    tags=["market"],
    dependencies=[Depends(get_current_user)],
)

_SORTABLE = {"score", "lead", "business", "refs", "produkt", "vendor", "kategorie", "prio"}


class Filters:
    """Filterparameter als Abhängigkeit — damit jeder Endpunkt exakt dieselbe
    Menge sieht wie die Trefferliste."""

    def __init__(
        self,
        q: str | None = Query(None, description="Volltext über Produkt, Prozesse, KI-Ideen"),
        kategorie: str | None = Query(None),
        branche: str | None = Query(None),
        regulatorik: str | None = Query(None),
        prio: str | None = Query(None, description="Kommaliste, z. B. A,B"),
        integration: str | None = Query(None, description="Kommaliste: leicht,mittel,schwer"),
        ref_status: str | None = Query(None, description="Kommaliste"),
        bearbeitung: str | None = Query(None, description="Kommaliste der Marktradar-Status"),
        marketplace: bool | None = Query(None),
        hat_regulatorik: bool | None = Query(None),
        min_lead: int = Query(1, ge=1, le=10),
        min_business: int = Query(1, ge=1, le=10),
        min_refs: int = Query(0, ge=0),
        baustein: int | None = Query(None, description="nur Produkte dieses Bausteins"),
    ):
        self.q = (q or "").strip().lower()
        self.kategorie = kategorie
        self.branche = branche
        self.regulatorik = regulatorik
        self.prio = _split(prio)
        self.integration = _split(integration)
        self.ref_status = _split(ref_status)
        self.bearbeitung = _split(bearbeitung)
        self.marketplace = marketplace
        self.hat_regulatorik = hat_regulatorik
        self.min_lead = min_lead
        self.min_business = min_business
        self.min_refs = min_refs
        self.baustein = baustein


def _split(value: str | None) -> set[str]:
    return {v.strip() for v in (value or "").split(",") if v.strip()}


def _haystack(p: MarketProduct) -> str:
    teile = [p.produkt, p.hersteller, p.kategorie, p.zielgruppe or "", p.notiz or "",
             p.nutzen or "", p.integration or ""]
    for feld in (p.branchen, p.prozesse, p.ki, p.pains, p.nutzer, p.reg):
        teile.extend(feld or [])
    return " ".join(teile).lower()


async def _filtered(db: AsyncSession, f: Filters) -> list[MarketProduct]:
    """Ganze (owner-scoped) Menge laden und in Python filtern.

    Der Katalog hat rund 150 Zeilen — die Volltext- und JSON-Listen-Filter in SQL
    zu bauen brächte hier keinen messbaren Vorteil, aber sechs Stellen, an denen
    Liste und Aggregat auseinanderlaufen können.
    """
    rows = list((await db.execute(select(MarketProduct))).scalars().all())

    ids_of_baustein: set[str] | None = None
    if f.baustein is not None:
        b = (await db.execute(
            select(MarketBaustein).where(MarketBaustein.nr == f.baustein)
        )).scalar_one_or_none()
        ids_of_baustein = set(b.catalog_ids or []) if b else set()

    out = []
    for p in rows:
        if f.prio and p.prio not in f.prio:
            continue
        if f.integration and p.int_level not in f.integration:
            continue
        if f.ref_status and p.ref_status not in f.ref_status:
            continue
        if f.bearbeitung and p.status.value not in f.bearbeitung:
            continue
        if f.kategorie and p.kategorie != f.kategorie:
            continue
        if f.branche and f.branche not in (p.branchen or []):
            continue
        if f.regulatorik and f.regulatorik not in (p.reg or []):
            continue
        if f.marketplace is not None and bool(p.marketplace) != f.marketplace:
            continue
        if f.hat_regulatorik is not None and bool(p.reg) != f.hat_regulatorik:
            continue
        if p.lead < f.min_lead or p.business < f.min_business or p.refs < f.min_refs:
            continue
        if ids_of_baustein is not None and p.catalog_id not in ids_of_baustein:
            continue
        if f.q and f.q not in _haystack(p):
            continue
        out.append(p)
    return out


@router.get("/products", response_model=list[MarketProductResponse])
async def list_products(
    f: Filters = Depends(),
    sort_by: str = Query("score"),
    sort_dir: str = Query("desc"),
    limit: int = Query(0, ge=0, le=500, description="0 = alle"),
    db: AsyncSession = Depends(get_db),
) -> list[MarketProduct]:
    rows = await _filtered(db, f)
    key = sort_by if sort_by in _SORTABLE else "score"
    rows.sort(key=lambda p: (getattr(p, key) or 0) if key not in ("produkt", "vendor", "kategorie", "prio")
              else (getattr(p, key) or "").lower(),
              reverse=(sort_dir != "asc"))
    return rows[:limit] if limit else rows


@router.get("/stats", response_model=MarketStats)
async def get_stats(f: Filters = Depends(), db: AsyncSession = Depends(get_db)) -> dict:
    return agg.stats(await _filtered(db, f))


@router.get("/vendors", response_model=list[MarketVendor])
async def get_vendors(f: Filters = Depends(), db: AsyncSession = Depends(get_db)) -> list[dict]:
    return agg.vendors(await _filtered(db, f))


@router.get("/konzerne")
async def get_konzerne(f: Filters = Depends(), db: AsyncSession = Depends(get_db)) -> list[dict]:
    return agg.konzerne(await _filtered(db, f))


@router.get("/categories", response_model=list[MarketCategory])
async def get_categories(f: Filters = Depends(), db: AsyncSession = Depends(get_db)) -> list[dict]:
    return agg.categories(await _filtered(db, f))


@router.get("/bausteine", response_model=list[MarketBausteinResponse])
async def get_bausteine(f: Filters = Depends(), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await _filtered(db, f)
    defs = list((await db.execute(select(MarketBaustein))).scalars().all())
    return agg.bausteine(rows, defs)


@router.get("/facets")
async def get_facets(db: AsyncSession = Depends(get_db)) -> dict:
    """Auswahlwerte für die Filter — immer aus dem VOLLEN Katalog, nicht aus der
    gefilterten Menge: sonst verschwindet der gerade gewählte Wert aus seiner
    eigenen Liste."""
    rows = list((await db.execute(select(MarketProduct))).scalars().all())
    branchen: set[str] = set()
    regs: set[str] = set()
    for p in rows:
        branchen.update(p.branchen or [])
        regs.update(p.reg or [])
    return {
        "kategorien": sorted({p.kategorie for p in rows}),
        "branchen": sorted(branchen),
        "regulatorik": sorted(regs),
        "ref_status": ["oeffentlich", "teilweise", "auf_anfrage", "unklar"],
        "integration": ["leicht", "mittel", "schwer"],
        "bearbeitung": [s.value for s in MarketStatus],
        "stand": rows[0].catalog_stand if rows else None,
        "gesamt": len(rows),
    }


async def _get_or_404(db: AsyncSession, product_id: uuid.UUID) -> MarketProduct:
    p = (await db.execute(
        select(MarketProduct).where(MarketProduct.id == product_id)
    )).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Katalogeintrag nicht gefunden")
    return p


@router.patch("/products/{product_id}", response_model=MarketProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: MarketProductUpdate,
    db: AsyncSession = Depends(get_db),
) -> MarketProduct:
    p = await _get_or_404(db, product_id)
    for feld, wert in data.model_dump(exclude_unset=True).items():
        setattr(p, feld, wert)
    await db.commit()
    await db.refresh(p)
    return p


@router.post("/products/{product_id}/to-pipeline", response_model=ToPipelineResponse)
async def push_to_pipeline(
    product_id: uuid.UUID,
    data: ToPipelineRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> ToPipelineResponse:
    p = await _get_or_404(db, product_id)
    body = data or ToPipelineRequest()

    lead, neu, grund = await to_pipeline(
        db, p, force=body.force, priority=body.priority, note=body.note
    )
    if grund and not body.force:
        # Werte VOR dem Rollback festhalten: danach sind die Attribute abgelaufen
        # und ein Zugriff löst einen Nachladeversuch auf der toten Transaktion aus.
        lead_id, company = str(lead.id), lead.company
        await db.rollback()
        raise HTTPException(status_code=409, detail={
            "message": f"Für „{company}“ gibt es bereits einen Lead. Trotzdem verknüpfen?",
            "reason": grund,
            "existing_id": lead_id,
            "existing_company": company,
        })
    await db.commit()
    return ToPipelineResponse(
        lead_id=lead.id, company=lead.company, created=neu, duplicate_reason=grund
    )
