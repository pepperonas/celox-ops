"""Zentrale Verwaltung feldbezogener Referenzwerte/Tags (Phase B2).

Werte bleiben als Freitext/JSON in den Records (Import/Dedup/CSV unverändert);
diese Schicht liefert die Verwaltung: auflisten (mit Verwendungszähler + Quelle),
umbenennen (global über alle Datensätze propagiert) und löschen (optional durch
einen anderen Wert ersetzen). Ein `ReferenceValue`-Eintrag hält zusätzlich selbst
erstellte, noch ungenutzte Werte samt Erstellungsdatum.

Wichtig (Tenancy): Bulk-`UPDATE`-Statements laufen NICHT durch die
Tenancy-SELECT-Events → sie filtern **explizit** auf `owner_id`. ORM-SELECTs sind
dagegen automatisch owner-scoped.

Die List-Umbau-Helfer sind rein und DB-frei getestet.
"""
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.rainmaker_lead import RainmakerLead
from app.models.reference_value import ReferenceValue
from app.models.time_entry import TimeEntry
from app.models.todo import Todo
from app.services.taxonomy import TAXONOMIES, canonicalize, fold
from app.tenancy import current_owner_id


@dataclass(frozen=True)
class _Store:
    model: type
    column: str
    kind: str  # 'scalar' | 'array'


# Feld → wo der Wert in den Records liegt. 'branche' teilt sich die Tags mit 'tag'
# (bewusst über 'tag' verwaltet, nicht doppelt). 'zielsystem' hat keine
# Record-Quelle (rein kuratiert + eigene Referenzwerte).
FIELD_STORES: dict[str, _Store] = {
    "role": _Store(RainmakerLead, "role", "scalar"),
    "source": _Store(RainmakerLead, "source", "scalar"),
    "target": _Store(RainmakerLead, "target", "scalar"),
    "tag": _Store(RainmakerLead, "tags", "array"),
    "vendor": _Store(Expense, "vendor", "scalar"),
    "taetigkeit": _Store(TimeEntry, "description", "scalar"),
    "todo": _Store(Todo, "title", "scalar"),
}

# Verwaltbare Felder + Anzeigelabel (branche NICHT separat = tag).
FIELD_LABELS: dict[str, str] = {
    "tag": "Tags / Branchen",
    "source": "Leadquellen",
    "role": "Ansprechpartner-Rollen",
    "target": "Targets (Verkaufs-Winkel)",
    "vendor": "Anbieter (Ausgaben)",
    "taetigkeit": "Tätigkeiten (Zeiterfassung)",
    "todo": "To-do-Titel",
    "zielsystem": "Zielsysteme",
}
MANAGED_FIELDS = tuple(FIELD_LABELS.keys())


# --------------------------------------------------------------------------- #
#  Reine Helfer (DB-frei, getestet)
# --------------------------------------------------------------------------- #
def rename_in_list(values: list | None, old_fold: str, new: str) -> tuple[list, bool]:
    """Ersetzt jeden Eintrag mit fold==old_fold durch `new`, dedupliziert
    fold-basiert (erste Schreibweise gewinnt) und erhält die Reihenfolge.
    Rückgabe: (neue_liste, geändert?)."""
    out: list = []
    seen: set[str] = set()
    changed = False
    for v in values or []:
        hit = fold(v) == old_fold
        rep = new if hit else v
        if hit and v != new:
            changed = True
        f = fold(rep)
        if f in seen:
            changed = True  # Dublette gefallen
            continue
        seen.add(f)
        out.append(rep)
    return out, changed


def remove_from_list(values: list | None, val_fold: str) -> tuple[list, bool]:
    """Entfernt alle Einträge mit fold==val_fold. Rückgabe: (neue_liste, geändert?)."""
    src = values or []
    out = [v for v in src if fold(v) != val_fold]
    return out, len(out) != len(src)


# --------------------------------------------------------------------------- #
#  DB-Operationen (owner-scoped)
# --------------------------------------------------------------------------- #
async def _record_counts(field: str, db: AsyncSession) -> dict[str, int]:
    """Verwendungshäufigkeit je kanonischem Wert aus den Records (owner-scoped)."""
    store = FIELD_STORES.get(field)
    counts: dict[str, int] = {}
    if store is None:
        return counts
    col = getattr(store.model, store.column)
    rows = (await db.execute(select(col))).scalars().all()  # ORM-SELECT → owner-gefiltert
    for r in rows:
        items = r if store.kind == "array" else [r]
        for v in items or []:
            v = (v or "").strip()
            if not v:
                continue
            c = canonicalize(field, v)
            counts[c] = counts.get(c, 0) + 1
    return counts


async def list_values(field: str, db: AsyncSession) -> list[dict]:
    """Kuratierte Werte ∪ eigene Referenzwerte ∪ Bestandswerte aus Records —
    fold-dedupliziert, mit Verwendungszähler + `custom`-Flag. Sortiert nach
    Verwendung desc, dann alphabetisch."""
    curated = {fold(v): v for v in TAXONOMIES.get(field, [])}
    entries: dict[str, dict] = {
        f: {"value": v, "count": 0, "custom": False, "created_at": None}
        for f, v in curated.items()
    }
    refs = (await db.execute(
        select(ReferenceValue).where(ReferenceValue.field == field)
    )).scalars().all()
    for r in refs:
        f = fold(r.value)
        entries.setdefault(f, {
            "value": r.value, "count": 0, "custom": f not in curated,
            "created_at": r.created_at,
        })
    for val, n in (await _record_counts(field, db)).items():
        f = fold(val)
        entry = entries.get(f)
        if entry is None:
            entry = {"value": val, "count": 0, "custom": f not in curated, "created_at": None}
            entries[f] = entry
        entry["count"] += n
    out = list(entries.values())
    out.sort(key=lambda e: (-e["count"], e["value"].lower()))
    return out


async def create_value(field: str, value: str, db: AsyncSession) -> str:
    """Legt einen eigenen Wert an (feldbezogen). Kuratierte oder bereits
    getrackte Werte sind ein No-op. Rückgabe: die kanonische Schreibweise."""
    v = canonicalize(field, value)
    if not v:
        raise ValueError("Leerer Wert.")
    if fold(v) in {fold(x) for x in TAXONOMIES.get(field, [])}:
        return v  # schon kuratiert
    existing = (await db.execute(
        select(ReferenceValue).where(ReferenceValue.field == field)
    )).scalars().all()
    if any(fold(r.value) == fold(v) for r in existing):
        return v
    db.add(ReferenceValue(field=field, value=v))
    await db.flush()
    return v


async def _sync_ref_after_change(field: str, old_fold: str, new_value: str | None,
                                 db: AsyncSession) -> None:
    """Entfernt Referenzwert-Einträge mit fold==old_fold; trackt `new_value`, wenn
    es ein eigener (nicht kuratierter) Wert ist."""
    refs = (await db.execute(
        select(ReferenceValue).where(ReferenceValue.field == field)
    )).scalars().all()
    for r in refs:
        if fold(r.value) == old_fold:
            await db.delete(r)
    if not new_value:
        return
    curated = {fold(v) for v in TAXONOMIES.get(field, [])}
    if fold(new_value) in curated:
        return
    remaining = [r for r in refs if fold(r.value) != old_fold]
    if not any(fold(r.value) == fold(new_value) for r in remaining):
        db.add(ReferenceValue(field=field, value=new_value))


async def rename_value(field: str, old: str, new: str, db: AsyncSession) -> dict:
    """Benennt `old` → `new` um und propagiert global auf alle eigenen Datensätze
    (fold-basiert, dedupliziert). Rückgabe: {affected, value}."""
    new_c = canonicalize(field, new)
    old_fold = fold(old)
    if not old_fold or not new_c:
        raise ValueError("Alter und neuer Wert erforderlich.")
    owner = current_owner_id.get()
    affected = 0
    store = FIELD_STORES.get(field)
    if store is not None:
        col = getattr(store.model, store.column)
        if store.kind == "scalar":
            raws = [r for r in (await db.execute(select(col).distinct())).scalars().all()
                    if r and fold(r) == old_fold and r != new_c]
            if raws:
                res = await db.execute(
                    update(store.model)
                    .where(store.model.owner_id == owner, col.in_(raws))
                    .values({store.column: new_c})
                )
                affected = res.rowcount or 0
        else:
            rows = (await db.execute(
                select(store.model).where(col.isnot(None))
            )).scalars().all()
            for row in rows:
                newlist, changed = rename_in_list(getattr(row, store.column), old_fold, new_c)
                if changed:
                    setattr(row, store.column, newlist)
                    affected += 1
    await _sync_ref_after_change(field, old_fold, new_c, db)
    await db.flush()
    return {"affected": affected, "value": new_c}


async def delete_value(field: str, value: str, db: AsyncSession,
                       replace_with: str | None = None) -> dict:
    """Löscht `value` aus allen eigenen Datensätzen. Mit `replace_with` = Umbenennen
    (Referenzen bleiben erhalten). Rückgabe: {affected, replaced}."""
    if replace_with and replace_with.strip():
        res = await rename_value(field, value, replace_with, db)
        return {"affected": res["affected"], "replaced": res["value"]}
    old_fold = fold(value)
    if not old_fold:
        raise ValueError("Wert erforderlich.")
    owner = current_owner_id.get()
    affected = 0
    store = FIELD_STORES.get(field)
    if store is not None:
        col = getattr(store.model, store.column)
        if store.kind == "scalar":
            raws = [r for r in (await db.execute(select(col).distinct())).scalars().all()
                    if r and fold(r) == old_fold]
            if raws:
                res = await db.execute(
                    update(store.model)
                    .where(store.model.owner_id == owner, col.in_(raws))
                    .values({store.column: None})
                )
                affected = res.rowcount or 0
        else:
            rows = (await db.execute(
                select(store.model).where(col.isnot(None))
            )).scalars().all()
            for row in rows:
                newlist, changed = remove_from_list(getattr(row, store.column), old_fold)
                if changed:
                    setattr(row, store.column, newlist)
                    affected += 1
    await _sync_ref_after_change(field, old_fold, None, db)
    await db.flush()
    return {"affected": affected, "replaced": None}


async def usage_count(field: str, value: str, db: AsyncSession) -> int:
    counts = await _record_counts(field, db)
    vf = fold(value)
    return sum(n for v, n in counts.items() if fold(v) == vf)
