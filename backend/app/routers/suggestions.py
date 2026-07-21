"""Generischer Autocomplete-Endpoint: kuratierte Taxonomie ∪ eigene Bestandswerte.

GET /api/suggestions?field=role&q=&limit= → {field, values, synonyms}
Owner-scoped (Tenancy filtert die ORM-SELECTs automatisch). Die Listen sind klein
(<300) — der Client lädt einmal pro Feld und filtert lokal; q wird trotzdem
serverseitig unterstützt.
"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.expense import Expense
from app.models.rainmaker_lead import RainmakerLead
from app.models.time_entry import TimeEntry
from app.models.todo import Todo
from app.services.taxonomy import SYNONYMS, TAXONOMIES, merge_suggestions

router = APIRouter(
    prefix="/api/suggestions",
    tags=["suggestions"],
    dependencies=[Depends(get_current_user)],
)

# Tags, die Import-Automatik sind, keine fachliche Branche (für field=branche).
_GENERIC_TAGS = {"discovery", "rainmaker", "linkedin", "ki-recherche", "vorgemerkt"}


async def _own_counts(field: str, db: AsyncSession) -> dict[str, int]:
    """Häufigkeiten der eigenen Bestandswerte je Feld (owner-scoped via Tenancy)."""
    counts: Counter[str] = Counter()
    if field == "role":
        rows = (await db.execute(select(RainmakerLead.role))).scalars().all()
        counts.update(r.strip() for r in rows if r and r.strip())
    elif field == "source":
        rows = (await db.execute(select(RainmakerLead.source))).scalars().all()
        counts.update(r.strip() for r in rows if r and r.strip())
    elif field in ("tag", "branche"):
        rows = (await db.execute(select(RainmakerLead.tags))).scalars().all()
        for tags in rows:
            for t in tags or []:
                t = (t or "").strip()
                if not t:
                    continue
                if field == "branche" and t.lower() in _GENERIC_TAGS:
                    continue
                counts[t] += 1
    elif field == "vendor":
        rows = (await db.execute(select(Expense.vendor))).scalars().all()
        counts.update(r.strip() for r in rows if r and r.strip())
    elif field == "taetigkeit":
        rows = (await db.execute(select(TimeEntry.description))).scalars().all()
        counts.update(r.strip() for r in rows if r and r.strip())
    elif field == "todo":
        rows = (await db.execute(select(Todo.title))).scalars().all()
        counts.update(r.strip() for r in rows if r and r.strip())
    elif field == "target":
        rows = (await db.execute(select(RainmakerLead.target))).scalars().all()
        counts.update(r.strip() for r in rows if r and r.strip())
    # zielsystem: rein kuratiert (keine DB-Quelle)
    return dict(counts)


@router.get("")
async def get_suggestions(
    field: str = Query(..., description="Feld-Key, z. B. role/source/tag/branche/zielsystem/vendor/taetigkeit/todo/target"),
    q: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if field not in TAXONOMIES:
        raise HTTPException(status_code=422, detail=f"Unbekanntes Feld '{field}'.")
    own = await _own_counts(field, db)
    return {
        "field": field,
        "values": merge_suggestions(field, own, q=q, limit=limit),
        "synonyms": SYNONYMS,
    }
