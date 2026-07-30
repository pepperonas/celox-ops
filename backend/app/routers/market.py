"""Marktradar — Recherchekatalog als eigene Sektion, mit Übergabe in die Pipeline.

GET    /api/market/products              → gefilterte Trefferliste
GET    /api/market/stats                 → Kennzahlen + Diagramm-Aggregate (folgen dem Filter)
GET    /api/market/vendors               → Hersteller-Rollup
GET    /api/market/konzerne              → Eigentümer mit mehr als einem Produkt
GET    /api/market/categories            → Kategorie-Rollup inkl. Risiken
GET    /api/market/bausteine             → Lösungsbausteine mit Reichweite
GET    /api/market/facets                → Auswahlwerte für die Filter
PATCH  /api/market/products/{id}         → eigener Bearbeitungsstand (Status, Notiz)
GET    /api/market/references             → Referenzkunden je (Firma, Hersteller), bewertet
GET    /api/market/references/firmen      → EINE Zeile je Firma mit allen Systemen (HAUPTSICHT)
GET    /api/market/references/firmen/{key} → eine Firma in ganzer Tiefe (Detail-Seite)
GET    /api/market/references/stats       → Kennzahlen der Kundensicht
PATCH  /api/market/references/{id}        → Bearbeitungsstand (verwerfen/zurückholen)
POST   /api/market/references/to-pipeline → ausgewählte Firmen als Leads anlegen
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
from app.models.market_reference import MarketReference
from app.models.market_product import MarketProduct, MarketStatus
from app.schemas.market import (
    MarketReferenceDetail,
    MarketReferenceGroupListe,
    MarketReferenceListe,
    MarketReferenceResponse,
    MarketReferenceStats,
    MarketReferenceUpdate,
    ReferencesToPipelineRequest,
    ReferencesToPipelineResponse,
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
from app.services.market_reference_pipeline import bausteine_fuer, reference_to_pipeline
from app.services.market_reference_scoring import SORTIERUNGEN, bewerte, orgtyp, sortiere

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


# ---------------------------------------------------------- Referenzkunden
#
# Der eigentliche Lead-Weg: nicht der Hersteller, sondern wer seine Software einsetzt.


@router.get("/references/stats", response_model=MarketReferenceStats)
async def reference_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Kennzahlen der Kundensicht — das, was den Marktradar jetzt beschreibt.

    Bewusst NICHT die Hersteller-Kennzahlen: Ziel sind die Anwender, der Katalog ist
    das Mittel. Die Herstellerzahlen bleiben unter `/stats` erreichbar.
    """
    zeilen = list((await db.execute(select(MarketReference))).scalars())
    systeme = _systeme_je_firma(zeilen)
    produkte = await _produkt_map(db, {r.product_id for r in zeilen})
    bausteine = list((await db.execute(select(MarketBaustein))).scalars())
    mit_baustein_ids = {
        p.id for p in produkte.values() if bausteine_fuer(p.catalog_id, bausteine)
    }

    typen: dict[str, int] = {}
    mit_baustein = 0
    for r in zeilen:
        typen[orgtyp(r.company)] = typen.get(orgtyp(r.company), 0) + 1
        if r.product_id in mit_baustein_ids:
            mit_baustein += 1

    top = sorted(
        ({"label": p.hersteller, "value": n} for p, n in
         _je_hersteller(zeilen, produkte).items()),
        key=lambda x: -x["value"])[:8]

    return {
        "firmen": len(zeilen),
        "firmen_distinkt": len(systeme),
        "mehrfachnutzer": sum(1 for n in systeme.values() if n > 1),
        "mit_baustein": mit_baustein,
        "mit_website": sum(1 for r in zeilen if r.website),
        "offen": sum(1 for r in zeilen if r.status == "neu"),
        "in_pipeline": sum(1 for r in zeilen if r.status == "in_pipeline"),
        "verworfen": sum(1 for r in zeilen if r.status == "verworfen"),
        "verzeichnisse": len({r.product_id for r in zeilen}),
        "orgtypen": [{"label": k, "value": v} for k, v in
                     sorted(typen.items(), key=lambda x: -x[1])],
        "top_hersteller": top,
    }


def _systeme_je_firma(zeilen: list[MarketReference]) -> dict[str, int]:
    """Wie viele verschiedene Hersteller-Systeme nutzt jede Firma?

    Das stärkste Pro-Kunde-Signal im ganzen Datensatz — und nur als Aggregat über den
    GESAMTEN Bestand berechenbar, nicht über die gefilterte Seite: Wer nach einem
    Hersteller filtert, würde sonst bei jeder Firma „1 System" sehen.
    """
    aus: dict[str, set] = {}
    for r in zeilen:
        aus.setdefault(r.company_norm, set()).add(r.product_id)
    return {k: len(v) for k, v in aus.items()}


async def _produkt_map(db: AsyncSession, ids: set) -> dict:
    if not ids:
        return {}
    return {p.id: p for p in (await db.execute(
        select(MarketProduct).where(MarketProduct.id.in_(ids)))).scalars()}


def _je_hersteller(zeilen: list[MarketReference], produkte: dict) -> dict:
    aus: dict = {}
    for r in zeilen:
        p = produkte.get(r.product_id)
        if p is not None:
            aus[p] = aus.get(p, 0) + 1
    return aus


@router.get("/references", response_model=MarketReferenceListe)
async def list_references(
    product_id: uuid.UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    mit_website: bool | None = None,
    nur_mehrfach: bool = False,
    orgtyp_filter: str | None = Query(None, alias="orgtyp"),
    sort: str = Query("score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Referenzkunden, bewertet und sortiert — die Hauptsicht des Marktradars.

    **Der Score entsteht in Python, nicht in SQL** (`market_reference_scoring`): Er
    hängt an einem Aggregat über den gesamten Bestand (Systemzahl je Firma) und ist
    keine Spalte. Deshalb wird die gefilterte Menge vollständig geladen, bewertet,
    sortiert und erst dann paginiert — dieselbe Entscheidung wie bei den
    Katalog-Aggregaten und aus demselben Grund (Abweichungen zwischen Liste und
    Kennzahl entstehen genau dort, wo beides getrennt gerechnet wird).
    """
    if sort not in SORTIERUNGEN:
        raise HTTPException(status_code=422, detail=f"sort muss aus {SORTIERUNGEN} sein")

    # Systemzahl IMMER über den gesamten Bestand (s. _systeme_je_firma).
    alle = list((await db.execute(select(MarketReference))).scalars())
    systeme = _systeme_je_firma(alle)

    zeilen = alle
    if product_id:
        zeilen = [r for r in zeilen if r.product_id == product_id]
    if status:
        zeilen = [r for r in zeilen if r.status == status]
    if mit_website is True:
        zeilen = [r for r in zeilen if r.website]
    elif mit_website is False:
        zeilen = [r for r in zeilen if not r.website]
    if nur_mehrfach:
        zeilen = [r for r in zeilen if systeme.get(r.company_norm, 1) > 1]
    if q:
        nadel = q.strip().lower()
        zeilen = [r for r in zeilen if nadel in r.company.lower()]
    if orgtyp_filter:
        zeilen = [r for r in zeilen if orgtyp(r.company) == orgtyp_filter]

    produkte = await _produkt_map(db, {r.product_id for r in zeilen})
    bausteine = list((await db.execute(select(MarketBaustein))).scalars())

    bewertet = []
    for r in zeilen:
        p = produkte.get(r.product_id)
        passend = bausteine_fuer(p.catalog_id, bausteine) if p else []
        b = bewerte(
            company=r.company,
            systeme=systeme.get(r.company_norm, 1),
            hat_baustein=bool(passend),
            produkt_score=p.score if p else 0,
            hat_website=bool(r.website),
        )
        bewertet.append({
            "id": r.id, "company": r.company, "website": r.website,
            "source_url": r.source_url, "form": r.form, "status": r.status,
            "rainmaker_lead_id": r.rainmaker_lead_id, "product_id": r.product_id,
            "produkt": p.produkt if p else None,
            "hersteller": p.hersteller if p else None,
            "kategorie": p.kategorie if p else None,
            "score": b["score"], "score_teile": b["score_teile"],
            "orgtyp": b["orgtyp"], "systeme": b["systeme"],
            "baustein_nr": passend[0].nr if passend else None,
            "baustein_titel": passend[0].titel if passend else None,
        })

    bewertet = sortiere(bewertet, sort)
    gesamt = len(bewertet)
    start = (page - 1) * page_size
    return {"items": bewertet[start:start + page_size], "total": gesamt, "page": page,
            "page_size": page_size, "pages": max(1, (gesamt + page_size - 1) // page_size)}


def _bester_name(namen: list[str]) -> str:
    """Aus mehreren Schreibweisen derselben Firma die vollständigste wählen. Rein.

    „Edeka" und „EDEKA" sind dieselbe Firma (gleicher `company_norm`), stehen aber in
    verschiedenen Verzeichnissen verschieden da. Genommen wird die längste Fassung —
    sie trägt meist die Rechtsform mit („Würth GmbH & Co. KG" statt „Würth"). Bei
    gleicher Länge alphabetisch, damit die Anzeige nicht zwischen zwei Aufrufen wechselt.
    """
    return sorted(namen, key=lambda n: (-len(n), n))[0]


@router.get("/references/firmen", response_model=MarketReferenceGroupListe)
async def list_reference_companies(
    f: Filters = Depends(),
    product_id: uuid.UUID | None = None,
    q: str | None = None,
    status: str | None = None,
    nur_mehrfach: bool = False,
    orgtyp_filter: str | None = Query(None, alias="orgtyp"),
    mit_baustein: bool | None = None,
    sort: str = Query("score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """**Die Hauptsicht: eine Zeile je Firma, mit allen Systemen, nach Score sortiert.**

    Ungruppiert erschien eine Firma mit drei Systemen dreimal und belegte die Spitze
    mehrfach (live gesehen: Edeka, August Storck, DAW SE). Für die Frage „welche Kunden
    lohnen sich" ist die Firma die Einheit.

    Ein Push nimmt **alle** Referenz-IDs der Firma mit: Die Namens-Dedup in
    `reference_to_pipeline` legt dann EINEN Lead an und hängt die Briefings der
    weiteren Systeme an — genau das, was man im Gespräch braucht.
    """
    if sort not in SORTIERUNGEN:
        raise HTTPException(status_code=422, detail=f"sort muss aus {SORTIERUNGEN} sein")

    alle = list((await db.execute(select(MarketReference))).scalars())
    # **Der geteilte Filter wirkt auch hier.** Er filtert Produkte (Kategorie, Branche,
    # Priorität, Integrationsaufwand, Baustein); die Kundensicht erbt das über den
    # Hersteller. Genau das ist der Arbeitsablauf: „Kategorie Zeiterfassung" → deren
    # Anwender. Vorher lief die Filterleiste auf dieser Seite ins Leere, obwohl sie
    # sichtbar darüber stand.
    #
    # Nur wenn wirklich gefiltert wird: `f.aktiv` zu prüfen wäre hier falsch, denn ein
    # leerer Filter liefert ohnehin alle Produkte — aber der Vergleich spart bei 4.000
    # Zeilen einen Durchlauf.
    erlaubte = {p.id for p in await _filtered(db, f)}
    zeilen_gefiltert = [r for r in alle if r.product_id in erlaubte]
    produkte = await _produkt_map(db, {r.product_id for r in alle})
    bausteine = list((await db.execute(select(MarketBaustein))).scalars())

    # Systemzahl IMMER über den gesamten Bestand: Wer nach einem Hersteller filtert,
    # soll trotzdem sehen, dass die Firma noch zwei andere Systeme einsetzt.
    systeme_gesamt: dict[str, set] = {}
    for r in alle:
        systeme_gesamt.setdefault(r.company_norm, set()).add(r.product_id)

    gruppen: dict[str, list[MarketReference]] = {}
    for r in zeilen_gefiltert:
        gruppen.setdefault(r.company_norm, []).append(r)

    items = []
    for schluessel, zeilen in gruppen.items():
        namen = _bester_name([r.company for r in zeilen])
        systeme_liste = []
        hat_baustein = False
        best_score = 0
        for r in sorted(zeilen, key=lambda x: x.company):
            p = produkte.get(r.product_id)
            passend = bausteine_fuer(p.catalog_id, bausteine) if p else []
            hat_baustein = hat_baustein or bool(passend)
            best_score = max(best_score, p.score if p else 0)
            systeme_liste.append({
                "reference_id": r.id, "product_id": r.product_id,
                "produkt": p.produkt if p else None,
                "hersteller": p.hersteller if p else None,
                "source_url": r.source_url,
                "baustein_nr": passend[0].nr if passend else None,
                "baustein_titel": passend[0].titel if passend else None,
            })
        website = next((r.website for r in zeilen if r.website), None)
        # Ein Stand für die Firma: „in der Pipeline" gewinnt, weil der Lead existiert.
        stand = ("in_pipeline" if any(r.status == "in_pipeline" for r in zeilen)
                 else "neu" if any(r.status == "neu" for r in zeilen) else "verworfen")
        # Die Systemzahl zählt VERSCHIEDENE Hersteller-Produkte über den ganzen
        # Bestand — nicht die gefilterten Zeilen (s. oben).
        anzahl = len(systeme_gesamt.get(schluessel, {r.product_id for r in zeilen}))
        b = bewerte(company=namen, systeme=anzahl, hat_baustein=hat_baustein,
                    produkt_score=best_score, hat_website=bool(website))
        items.append({
            "company": namen, "company_norm": schluessel, "website": website,
            "status": stand, "score": b["score"], "score_teile": b["score_teile"],
            "orgtyp": b["orgtyp"], "systeme": anzahl,
            "reference_ids": [r.id for r in zeilen],
            "produkte": systeme_liste,
            # Angereicherte Werte: erster nicht-leerer über die Nennungen — sie gehören
            # der Firma, nicht dem Paar.
            "email": next((r.email for r in zeilen if r.email), None),
            "phone": next((r.phone for r in zeilen if r.phone), None),
            "decision_maker": next((r.decision_maker for r in zeilen if r.decision_maker), None),
            "_hat_baustein": hat_baustein,
        })

    if product_id:
        # Aus dem Produkt-Dossier heraus: nur die Anwender DIESER Software.
        items = [i for i in items
                 if any(p["product_id"] == product_id for p in i["produkte"])]
    if q:
        nadel = q.strip().lower()
        items = [i for i in items if nadel in i["company"].lower()]
    if status:
        items = [i for i in items if i["status"] == status]
    if nur_mehrfach:
        items = [i for i in items if i["systeme"] > 1]
    if orgtyp_filter:
        items = [i for i in items if i["orgtyp"] == orgtyp_filter]
    if mit_baustein is not None:
        items = [i for i in items if i["_hat_baustein"] is mit_baustein]
    for i in items:
        i.pop("_hat_baustein", None)

    items = sortiere(items, sort)
    gesamt = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": gesamt, "page": page,
            "page_size": page_size, "pages": max(1, (gesamt + page_size - 1) // page_size)}


@router.get("/references/firmen/{company_norm}", response_model=MarketReferenceDetail)
async def reference_company_detail(
    company_norm: str, db: AsyncSession = Depends(get_db),
) -> dict:
    """Eine Firma in ganzer Tiefe.

    Angesprochen über `company_norm` und nicht über eine ID: Die Firma ist hier keine
    Zeile, sondern eine Gruppe von Zeilen (eine je Hersteller). Der normalisierte Name
    IST ihr Schlüssel — genau der, über den auch die Eindeutigkeit läuft.
    """
    zeilen = list((await db.execute(
        select(MarketReference).where(MarketReference.company_norm == company_norm)
    )).scalars())
    if not zeilen:
        raise HTTPException(status_code=404, detail="Firma nicht gefunden")

    produkte = await _produkt_map(db, {r.product_id for r in zeilen})
    alle_bausteine = list((await db.execute(select(MarketBaustein))).scalars())

    systeme_liste, passende = [], {}
    for r in sorted(zeilen, key=lambda x: x.company):
        p = produkte.get(r.product_id)
        treffer = bausteine_fuer(p.catalog_id, alle_bausteine) if p else []
        for b in treffer:
            passende[b.nr] = b
        systeme_liste.append({
            "reference_id": r.id, "product_id": r.product_id,
            "produkt": p.produkt if p else None,
            "hersteller": p.hersteller if p else None,
            "source_url": r.source_url,
            "baustein_nr": treffer[0].nr if treffer else None,
            "baustein_titel": treffer[0].titel if treffer else None,
        })

    # Kontaktdaten gehören der Firma: erster nicht-leerer Wert über alle Nennungen.
    def zuerst(feld: str):
        return next((getattr(r, feld) for r in zeilen if getattr(r, feld, None)), None)

    anzahl = len({r.product_id for r in zeilen})
    beleg: dict = {}
    for r in zeilen:
        beleg.update(r.contact_evidence or {})
    b = bewerte(company=_bester_name([r.company for r in zeilen]), systeme=anzahl,
                hat_baustein=bool(passende),
                produkt_score=max((p.score for p in produkte.values()), default=0),
                hat_website=bool(zuerst("website")))
    return {
        "company": _bester_name([r.company for r in zeilen]),
        "company_norm": company_norm,
        "website": zuerst("website"), "website_source": zuerst("website_source"),
        "email": zuerst("email"), "email_status": zuerst("email_status"),
        "phone": zuerst("phone"), "decision_maker": zuerst("decision_maker"),
        "employee_count": zuerst("employee_count"), "address": zuerst("address"),
        "contact_evidence": beleg or None,
        "contact_checked_at": zuerst("contact_checked_at"),
        "status": ("in_pipeline" if any(r.status == "in_pipeline" for r in zeilen)
                   else "neu" if any(r.status == "neu" for r in zeilen) else "verworfen"),
        "score": b["score"], "score_teile": b["score_teile"], "orgtyp": b["orgtyp"],
        "systeme": anzahl,
        "reference_ids": [r.id for r in zeilen],
        "rainmaker_lead_id": zuerst("rainmaker_lead_id"),
        "produkte": systeme_liste,
        "bausteine": [{"nr": b2.nr, "titel": b2.titel, "was": b2.was,
                       "warum": b2.warum, "aufwand": b2.aufwand}
                      for b2 in sorted(passende.values(), key=lambda x: x.nr)],
    }


@router.patch("/references/{reference_id}", response_model=MarketReferenceResponse)
async def update_reference(
    reference_id: uuid.UUID,
    data: MarketReferenceUpdate,
    db: AsyncSession = Depends(get_db),
) -> MarketReference:
    r = (await db.execute(
        select(MarketReference).where(MarketReference.id == reference_id)
    )).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Referenz nicht gefunden")
    if data.status is not None:
        r.status = data.status
    await db.commit()
    await db.refresh(r)
    return r


@router.post("/references/to-pipeline", response_model=ReferencesToPipelineResponse)
async def push_references(
    data: ReferencesToPipelineRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Ausgewählte Referenzkunden als Leads anlegen.

    Mehrere auf einmal, weil das der Arbeitsablauf ist: Man sichtet eine Kundenliste
    und nimmt daraus zwanzig mit. Jede Firma läuft im eigenen SAVEPOINT — eine
    Kollision am Unique-Index stoppt die anderen nicht (Muster des Batch-Merge).

    Ein bereits vorhandener Lead wird **verknüpft und ergänzt**, nie dupliziert; ohne
    `force` erscheint er im Bericht als `verknuepft`.
    """
    if not data.ids:
        raise HTTPException(status_code=422, detail="Keine Auswahl übergeben")
    if len(data.ids) > 200:
        raise HTTPException(status_code=422, detail="Höchstens 200 auf einmal")

    referenzen = list((await db.execute(
        select(MarketReference).where(MarketReference.id.in_(data.ids)))).scalars())
    if not referenzen:
        raise HTTPException(status_code=404, detail="Keine der Firmen gefunden")
    produkte = {p.id: p for p in (await db.execute(
        select(MarketProduct).where(
            MarketProduct.id.in_({r.product_id for r in referenzen})))).scalars()}
    bausteine = list((await db.execute(select(MarketBaustein))).scalars())

    angelegt, verknuepft, fehler = [], [], []
    for r in referenzen:
        p = produkte.get(r.product_id)
        if p is None:
            fehler.append({"company": r.company, "reason": "Hersteller nicht gefunden"})
            continue
        try:
            async with db.begin_nested():
                lead, neu, grund = await reference_to_pipeline(
                    db, r, p, bausteine, force=data.force)
            eintrag = {"company": r.company, "lead_id": str(lead.id)}
            (angelegt if neu else verknuepft).append(eintrag)
        except Exception as exc:                    # eine Firma darf den Rest nicht kippen
            fehler.append({"company": r.company, "reason": type(exc).__name__})
    await db.commit()
    return {"created": angelegt, "linked": verknuepft, "failed": fehler}
