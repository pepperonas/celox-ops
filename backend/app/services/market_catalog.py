"""Marktradar: Aggregate für Kennzahlen, Diagramme, Hersteller und Kategorien.

Bewusst in Python statt als SQL-Aggregat: Der Katalog umfasst rund 150 Zeilen,
und **jedes** Aggregat muss demselben Filter folgen wie die Trefferliste. Mit
SQL-Aggregaten müsste jede Filterbedingung an sechs Stellen wiederholt werden —
genau dort entstehen die Abweichungen zwischen Diagramm und Liste.

Die fachlichen Regeln (Score, Marktplatz-Erkennung, Regulatorik, „Hersteller
besetzt den Use Case selbst") stehen NICHT hier, sondern im Recherche-Repo. Hier
werden nur die importierten Felder ausgewertet.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from app.models.market_baustein import MarketBaustein
from app.models.market_product import CLOSED_STATUSES, MarketProduct

_SCORE_BINS = [(0, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 100)]


def kat_short(kategorie: str) -> str:
    """Kurzform für enge Spalten und Achsen: „DMS / ECM / …" -> „DMS"."""
    return re.split(r"[,&/]", kategorie or "")[0].strip()


def _top(counter: Counter, n: int) -> list[dict]:
    return [{"label": k, "value": v} for k, v in counter.most_common(n)]


def stats(rows: list[MarketProduct]) -> dict:
    n = len(rows)
    if not n:
        return {
            "produkte": 0, "prio_a": 0, "verzeichnisse": 0, "hersteller": 0, "kategorien": 0,
            "referenzen": 0, "marketplace": 0, "regulatorik": 0, "integration_leicht": 0,
            "offen": 0, "in_pipeline": 0, "avg_lead": 0.0, "avg_business": 0.0, "avg_score": 0,
            "branchen": [], "kategorien_top": [], "reg_top": [], "lead_hist": [],
            "business_hist": [], "score_bins": [], "prio_bins": [], "int_bins": [], "status_bins": [],
        }

    branchen: Counter = Counter()
    kategorien: Counter = Counter()
    regs: Counter = Counter()
    for r in rows:
        branchen.update(r.branchen or [])
        kategorien.update([r.kategorie])
        regs.update(r.reg or [])

    return {
        "produkte": n,
        "prio_a": sum(1 for r in rows if r.prio == "A"),
        "verzeichnisse": sum(1 for r in rows if r.ref_status == "oeffentlich"),
        "hersteller": len({r.vendor_slug for r in rows}),
        "kategorien": len(kategorien),
        "referenzen": sum(r.refs for r in rows),
        "marketplace": sum(1 for r in rows if r.marketplace),
        "regulatorik": sum(1 for r in rows if r.reg),
        "integration_leicht": sum(1 for r in rows if r.int_level == "leicht"),
        "offen": sum(1 for r in rows if r.status not in CLOSED_STATUSES),
        "in_pipeline": sum(1 for r in rows if r.rainmaker_lead_id is not None),
        "avg_lead": round(sum(r.lead for r in rows) / n, 1),
        "avg_business": round(sum(r.business for r in rows) / n, 1),
        "avg_score": round(sum(r.score for r in rows) / n),
        "branchen": _top(branchen, 10),
        "kategorien_top": [{"label": kat_short(k), "value": v, "key": k}
                           for k, v in kategorien.most_common(10)],
        "reg_top": _top(regs, 8),
        "lead_hist": [{"label": str(i), "value": sum(1 for r in rows if r.lead == i)}
                      for i in range(1, 11)],
        "business_hist": [{"label": str(i), "value": sum(1 for r in rows if r.business == i)}
                          for i in range(1, 11)],
        "score_bins": [{"label": "80+" if lo == 80 else f"{lo}–{hi}",
                        "value": sum(1 for r in rows if lo <= r.score <= hi)}
                       for lo, hi in _SCORE_BINS],
        "prio_bins": [{"label": p, "value": sum(1 for r in rows if r.prio == p)}
                      for p in ("A", "B", "C")],
        "int_bins": [{"label": lvl, "value": sum(1 for r in rows if r.int_level == lvl)}
                     for lvl in ("leicht", "mittel", "schwer")],
        "status_bins": [{"label": s.value, "value": sum(1 for r in rows if r.status == s)}
                        for s in sorted({r.status for r in rows}, key=lambda x: x.value)],
    }


def vendors(rows: list[MarketProduct]) -> list[dict]:
    grouped: dict[str, list[MarketProduct]] = defaultdict(list)
    for r in rows:
        grouped[r.vendor_slug].append(r)

    out = []
    for slug, items in grouped.items():
        n = len(items)
        regs: set[str] = set()
        for i in items:
            regs.update(i.reg or [])
        out.append({
            "vendor": items[0].vendor,
            "vendor_slug": slug,
            "konzern": items[0].konzern,
            "produkte": n,
            "refs": sum(i.refs for i in items),
            "avg_lead": round(sum(i.lead for i in items) / n, 1),
            "avg_score": round(sum(i.score for i in items) / n),
            "marketplace": any(i.marketplace for i in items),
            "kategorien": sorted({i.kategorie for i in items}),
            "reg": sorted(regs),
            "catalog_ids": [i.catalog_id for i in items],
        })
    return sorted(out, key=lambda v: (-v["avg_score"], -v["refs"]))


def konzerne(rows: list[MarketProduct]) -> list[dict]:
    """Nur Eigentümer mit mehr als einem Produkt — ein Gespräch, mehrere Produkte."""
    grouped: dict[str, list[MarketProduct]] = defaultdict(list)
    for r in rows:
        grouped[r.konzern_slug or r.vendor_slug].append(r)

    out = []
    for slug, items in grouped.items():
        if len(items) < 2:
            continue
        out.append({
            "konzern": items[0].konzern or items[0].vendor,
            "konzern_slug": slug,
            "produkte": len(items),
            "refs": sum(i.refs for i in items),
            "marketplace": any(i.marketplace for i in items),
            "namen": [i.produkt for i in items],
            "catalog_ids": [i.catalog_id for i in items],
        })
    return sorted(out, key=lambda k: (-k["produkte"], -k["refs"]))


def categories(rows: list[MarketProduct]) -> list[dict]:
    grouped: dict[str, list[MarketProduct]] = defaultdict(list)
    for r in rows:
        grouped[r.kategorie].append(r)

    out = []
    for kategorie, items in grouped.items():
        n = len(items)
        best = sorted(items, key=lambda i: -i.score)
        prozesse: Counter = Counter()
        for i in items:
            prozesse.update(i.prozesse or [])

        # Risiken kommen aus den importierten Flags, nicht aus einer zweiten
        # Textanalyse — die Regel gehört ins Recherche-Repo.
        risiken = []
        for i in best:
            grund = []
            if i.int_level == "schwer":
                grund.append("Integration schwer")
            if i.ref_status in ("auf_anfrage", "unklar"):
                grund.append("kein belastbares Referenzverzeichnis")
            if i.self_compete:
                grund.append("Hersteller besetzt den Use Case selbst")
            if grund:
                risiken.append({"catalog_id": i.catalog_id, "produkt": i.produkt, "grund": grund})

        out.append({
            "kategorie": kategorie,
            "produkte": n,
            "refs": sum(i.refs for i in items),
            "avg_score": round(sum(i.score for i in items) / n),
            "avg_business": round(sum(i.business for i in items) / n, 1),
            "prio_a": sum(1 for i in items if i.prio == "A"),
            "marketplace": sum(1 for i in items if i.marketplace),
            "oeffentlich": sum(1 for i in items if i.ref_status == "oeffentlich"),
            "top": [{"catalog_id": i.catalog_id, "produkt": i.produkt, "score": i.score,
                     "ki": (i.ki or [None])[0]} for i in best[:3]],
            "prozesse": [{"label": k, "value": v} for k, v in prozesse.most_common(6)],
            "risiken": risiken[:5],
        })
    return sorted(out, key=lambda c: -c["avg_score"])


def bausteine(rows: list[MarketProduct], defs: list[MarketBaustein]) -> list[dict]:
    """Kennzahlen je Baustein gegen die **gefilterte** Produktmenge."""
    by_id = {r.catalog_id: r for r in rows}
    out = []
    for b in defs:
        treffer = [by_id[c] for c in (b.catalog_ids or []) if c in by_id]
        out.append({
            "nr": b.nr,
            "titel": b.titel,
            "was": b.was,
            "warum": b.warum,
            "vorsicht": b.vorsicht,
            "aufwand": b.aufwand,
            "catalog_ids": [t.catalog_id for t in sorted(treffer, key=lambda t: -t.score)],
            "treffer": len(treffer),
            "reach": sum(t.refs for t in treffer),
            "avg_score": round(sum(t.score for t in treffer) / len(treffer)) if treffer else 0,
            "kategorien": len({t.kategorie for t in treffer}),
        })
    return sorted(out, key=lambda b: (-b["treffer"], -b["reach"]))
