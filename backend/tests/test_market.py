"""DB-freie Tests fürs Marktradar-Modul.

Schwerpunkt ist die Regel, die beim Katalog-Update kaputtgehen kann: der eigene
Bearbeitungsstand (Status, Notiz, verknüpfter Lead) muss einen Re-Import
überleben. Dazu die Aggregate, die dem Filter folgen müssen, und die Ableitung
des Lead-Briefings.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

# MarketProduct zeigt per FK auf `rainmaker_leads`; SQLAlchemy konfiguriert dabei
# den ganzen Mapper-Graphen. Ohne die Registry fehlen dessen Nachbarmodelle und
# schon das Instanziieren im Speicher scheitert (genau der Fall aus registry.py).
from app.models import registry  # noqa: F401
from app.models.market_baustein import MarketBaustein
from app.models.market_product import MarketProduct, MarketStatus
from app.services import market_catalog as agg
from app.services.market_import import import_catalog
from app.services.market_pipeline import briefing, lead_tags, vendor_website


# ── Testdoubles ──────────────────────────────────────────────────────────────
class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """Minimale AsyncSession-Attrappe: nur, was import_catalog benutzt."""

    def __init__(self, products=None, bausteine=None):
        self.products = list(products or [])
        self.bausteine = list(bausteine or [])
        self.added = []
        self.deleted = []

    async def execute(self, stmt):
        entity = stmt.column_descriptions[0]["entity"]
        return _Result(self.products if entity is MarketProduct else self.bausteine)

    def add(self, obj):
        self.added.append(obj)
        (self.products if isinstance(obj, MarketProduct) else self.bausteine).append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)


def katalog_eintrag(cid="dvelop", **over):
    d = {
        "id": cid, "produkt": "d.velop documents", "hersteller": "d.velop AG, Gescher",
        "vendor": "d.velop AG", "vendorSlug": "d-velop-ag", "konzern": "d.velop AG",
        "konzernSlug": "d-velop-ag", "kategorie": "DMS / ECM / Dokumentenautomation",
        "refUrl": "https://www.d-velop.de/referenzen", "refStatus": "oeffentlich",
        "urlOk": True, "urlGeprueft": "ok", "refs": 200, "kunden": "15.000+ Organisationen",
        "zielgruppe": "Mittelstand", "branchen": ["Industrie"], "prozesse": ["Dokumentenmanagement"],
        "nutzer": ["Sachbearbeitung"], "pains": ["Freigabeprozesse nachhalten"],
        "ki": ["Audit-Dossier-Generator", "Vertragsmonitor"], "nutzen": "mehrere Personentage je Audit",
        "integration": "leicht - moderne Cloud-Plattform", "intLevel": "leicht", "ease": 1.0,
        "notiz": "Der d.velop store ist ein echter Marktplatz.", "lead": 9, "business": 9,
        "prio": "A", "dach": "hoch", "score": 89,
        "breakdown": [{"key": "business", "points": 25.2}],
        "marketplace": True, "mpEvidence": ["d.velop store"], "reg": ["NIS2"], "selfCompete": False,
    }
    d.update(over)
    return d


def produkt(**over):
    """MarketProduct im Speicher — SQLAlchemy-Modelle brauchen dafür keine DB."""
    felder = {
        "catalog_id": "x", "produkt": "P", "hersteller": "H GmbH", "vendor": "H GmbH",
        "vendor_slug": "h-gmbh", "konzern": "H GmbH", "konzern_slug": "h-gmbh",
        "kategorie": "ERP", "ref_url": "https://h.example/referenzen", "ref_status": "oeffentlich",
        "url_ok": True, "refs": 100, "branchen": ["Industrie"], "prozesse": ["Auftrag"],
        "nutzer": ["Innendienst"], "pains": ["abtippen"], "ki": ["Automat"], "int_level": "leicht",
        "lead": 8, "business": 8, "prio": "A", "score": 70, "marketplace": False,
        "reg": [], "self_compete": False, "status": MarketStatus.neu, "ease": Decimal("1.0"),
    }
    felder.update(over)
    return MarketProduct(**felder)


# ── Import: Idempotenz und Schutz des Bearbeitungsstands ─────────────────────
def test_import_legt_neue_eintraege_an():
    db = FakeSession()
    res = asyncio.run(import_catalog(db, {"stand": "2026-07-30", "produkte": [katalog_eintrag()],
                                          "bausteine": []}))
    assert res["angelegt"] == 1 and res["aktualisiert"] == 0
    row = db.added[0]
    assert row.catalog_id == "dvelop"
    assert row.score == 89 and row.marketplace is True
    assert row.mp_evidence == ["d.velop store"]
    assert row.catalog_stand == "2026-07-30"


def test_zweiter_import_erzeugt_keine_dublette():
    bestehend = produkt(catalog_id="dvelop", score=89)
    db = FakeSession(products=[bestehend])
    res = asyncio.run(import_catalog(db, {"stand": "2026-07-30", "produkte": [katalog_eintrag()],
                                          "bausteine": []}))
    assert res["angelegt"] == 0
    assert [o for o in db.added if isinstance(o, MarketProduct)] == []


def test_reimport_erhaelt_bearbeitungsstand():
    """Regressionsschutz: Ein Katalog-Update darf die eigene Arbeit nicht löschen."""
    import uuid as _uuid
    lead_id = _uuid.uuid4()
    bestehend = produkt(
        catalog_id="dvelop", score=10, produkt="alter Name",
        status=MarketStatus.in_pipeline, ops_note="angeschrieben am 12.",
        rainmaker_lead_id=lead_id,
        forum_pains=["Forum-Punkt"],
        vendor_gaps=["Lücke"],
        remedies=["Lösung"],
    )
    db = FakeSession(products=[bestehend])
    asyncio.run(import_catalog(db, {"stand": "2026-08-01", "produkte": [katalog_eintrag()],
                                    "bausteine": []}))
    # Katalogfelder aktualisiert …
    assert bestehend.score == 89
    assert bestehend.produkt == "d.velop documents"
    assert bestehend.catalog_stand == "2026-08-01"
    # … ops-Felder unangetastet
    assert bestehend.status is MarketStatus.in_pipeline
    assert bestehend.ops_note == "angeschrieben am 12."
    assert bestehend.rainmaker_lead_id == lead_id
    assert bestehend.forum_pains == ["Forum-Punkt"]
    assert bestehend.vendor_gaps == ["Lücke"]
    assert bestehend.remedies == ["Lösung"]


def test_import_meldet_verwaiste_eintraege_ohne_zu_loeschen():
    alt = produkt(catalog_id="verschwunden")
    db = FakeSession(products=[alt])
    res = asyncio.run(import_catalog(db, {"stand": "x", "produkte": [katalog_eintrag()],
                                          "bausteine": []}))
    assert res["verwaist"] == ["verschwunden"]
    assert alt not in db.deleted


def test_import_ohne_produkte_faellt_auf():
    db = FakeSession()
    try:
        asyncio.run(import_catalog(db, {"stand": "x", "produkte": [], "bausteine": []}))
    except ValueError:
        return
    raise AssertionError("leerer Katalog haette auffallen muessen")


def test_bausteine_werden_ersetzt_nicht_ergaenzt():
    alt = MarketBaustein(nr=1, titel="alt", catalog_ids=[])
    db = FakeSession(bausteine=[alt])
    asyncio.run(import_catalog(db, {
        "stand": "x", "produkte": [katalog_eintrag()],
        "bausteine": [{"nr": 1, "titel": "Sprache → Dokumentation", "was": "…", "ids": ["dvelop"]}],
    }))
    assert alt in db.deleted
    neu = [o for o in db.added if isinstance(o, MarketBaustein)]
    assert len(neu) == 1 and neu[0].titel == "Sprache → Dokumentation"


# ── Aggregate ────────────────────────────────────────────────────────────────
def test_stats_zaehlt_die_uebergebene_menge():
    rows = [produkt(catalog_id="a", score=80, prio="A", marketplace=True, reg=["NIS2"]),
            produkt(catalog_id="b", score=60, prio="B", ref_status="teilweise", int_level="mittel")]
    s = agg.stats(rows)
    assert s["produkte"] == 2
    assert s["prio_a"] == 1
    assert s["verzeichnisse"] == 1
    assert s["marketplace"] == 1
    assert s["regulatorik"] == 1
    assert s["referenzen"] == 200
    assert s["avg_score"] == 70


def test_stats_auf_leerer_menge_bleibt_nutzbar():
    s = agg.stats([])
    assert s["produkte"] == 0 and s["avg_score"] == 0 and s["branchen"] == []


def test_vendors_fasst_produkte_desselben_herstellers_zusammen():
    rows = [produkt(catalog_id="a", vendor_slug="v", vendor="V AG", score=80, refs=10),
            produkt(catalog_id="b", vendor_slug="v", vendor="V AG", score=60, refs=5)]
    v = agg.vendors(rows)
    assert len(v) == 1
    assert v[0]["produkte"] == 2 and v[0]["refs"] == 15 and v[0]["avg_score"] == 70


def test_konzerne_zeigt_nur_eigentuemer_mit_mehreren_produkten():
    rows = [produkt(catalog_id="a", konzern_slug="ser", konzern="SER Group", vendor_slug="v1"),
            produkt(catalog_id="b", konzern_slug="ser", konzern="SER Group", vendor_slug="v2"),
            produkt(catalog_id="c", konzern_slug="allein", vendor_slug="v3")]
    k = agg.konzerne(rows)
    assert [x["konzern_slug"] for x in k] == ["ser"]
    assert k[0]["produkte"] == 2


def test_kategorie_risiken_kommen_aus_den_importierten_flags():
    rows = [
        produkt(catalog_id="a", kategorie="ERP", int_level="schwer"),
        produkt(catalog_id="b", kategorie="ERP", self_compete=True),
        produkt(catalog_id="c", kategorie="ERP", ref_status="unklar"),
        produkt(catalog_id="d", kategorie="ERP"),
    ]
    cat = agg.categories(rows)[0]
    gruende = {r["catalog_id"]: r["grund"] for r in cat["risiken"]}
    assert gruende["a"] == ["Integration schwer"]
    assert gruende["b"] == ["Hersteller besetzt den Use Case selbst"]
    assert gruende["c"] == ["kein belastbares Referenzverzeichnis"]
    assert "d" not in gruende


def test_bausteine_rechnen_gegen_die_gefilterte_menge():
    rows = [produkt(catalog_id="a", refs=100, score=80)]          # "b" ist herausgefiltert
    defs = [MarketBaustein(nr=1, titel="Sprache", catalog_ids=["a", "b"])]
    b = agg.bausteine(rows, defs)[0]
    assert b["treffer"] == 1
    assert b["reach"] == 100
    assert b["avg_score"] == 80


def test_kat_short_kuerzt_lange_kategorienamen():
    assert agg.kat_short("DMS / ECM / Dokumentenautomation") == "DMS"
    assert agg.kat_short("Logistik, Transport & Aussenhandel") == "Logistik"


# ── Übergabe in die Pipeline ─────────────────────────────────────────────────
def test_vendor_website_reduziert_die_referenz_url_auf_den_origin():
    assert vendor_website("https://www.d-velop.de/referenzen/details/x.html") == "https://www.d-velop.de"
    assert vendor_website("https://pit.de/success-stories/") == "https://pit.de"
    assert vendor_website("") is None
    assert vendor_website(None) is None


def test_briefing_enthaelt_die_verkaufsrelevanten_felder():
    p = produkt(ki=["Audit-Dossier-Generator"], pains=["Freigaben nachhalten"],
                nutzen="1-2 FTE", marketplace=True, mp_evidence=["d.velop store"],
                reg=["NIS2"], score=89, prio="A")
    text = briefing(p)
    assert "Opportunity Score 89" in text
    assert "Audit-Dossier-Generator" in text
    assert "Freigaben nachhalten" in text
    assert "d.velop store" in text
    assert "NIS2" in text
    assert p.ref_url in text


def test_briefing_warnt_bei_eigenkonkurrenz():
    assert "ACHTUNG" in briefing(produkt(self_compete=True))
    assert "ACHTUNG" not in briefing(produkt(self_compete=False))


def test_lead_tags_ohne_dubletten_mit_kurzer_kategorie():
    tags = lead_tags(produkt(kategorie="DMS / ECM / Dokumentenautomation",
                             marketplace=True, reg=["NIS2", "NIS2"]))
    assert tags == ["Marktradar", "DMS", "Marktplatz", "NIS2"]


def test_select_entity_erkennung_der_attrappe():
    """Schützt die Attrappe selbst: sie unterscheidet die beiden Tabellen."""
    assert select(MarketProduct).column_descriptions[0]["entity"] is MarketProduct
    assert select(MarketBaustein).column_descriptions[0]["entity"] is MarketBaustein
