import re
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.customer import Customer

router = APIRouter(
    prefix="/api/github",
    tags=["github"],
    dependencies=[Depends(get_current_user)],
)

# Cache: 10 min TTL
_cache: dict = {"data": None, "time": 0}
CACHE_TTL = 600

# Commit-type prefixes that describe maintenance rather than a feature — folded together.
_NOISE_THEMES = {
    "fix", "fixes", "bugfix", "hotfix", "docs", "doc", "doku", "dokumentation",
    "test", "tests", "chore", "ci", "refactor", "style", "build", "perf",
    "revert", "wip", "merge", "cleanup", "lint",
}
_MAINT_LABEL = "Wartung, Tests & Doku"
_SUMMARY_MARKER = "Erbrachte Leistungen ("


def _commit_theme(subject: str) -> str:
    """Derive a coarse theme from a commit subject (text before the first ':',
    with trailing '(…)', 'Phase N' and version numbers stripped)."""
    theme = subject.split(":", 1)[0].strip() if ":" in subject else subject.strip()
    theme = re.sub(r"\s*\([^)]*\)\s*$", "", theme).strip()  # trailing "(Paket 2)" etc.
    theme = re.sub(r"\s+(phase\s*\d+|v?\d+([.,]\d+)*)$", "", theme, flags=re.I).strip()
    if theme.lower() in _NOISE_THEMES:
        return _MAINT_LABEL
    return theme[:60]


@router.get("/repos")
async def list_repos() -> list:
    """Listet alle GitHub-Repos des konfigurierten Users (cached 10 min)."""
    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=503, detail="GitHub Token nicht konfiguriert")

    now = time.time()
    if _cache["data"] is not None and now - _cache["time"] < CACHE_TTL:
        return _cache["data"]

    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    repos = []
    page = 1
    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={"per_page": 100, "page": page, "sort": "pushed"},
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            for r in data:
                repos.append({
                    "full_name": r["full_name"],
                    "name": r["name"],
                    "private": r["private"],
                    "pushed_at": r.get("pushed_at"),
                })
            page += 1
            if len(data) < 100:
                break

    _cache["data"] = repos
    _cache["time"] = now
    return repos


@router.get("/summary")
async def commit_summary(
    customer_id: uuid.UUID = Query(...),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Kompakte, gruppierte Leistungsbeschreibung aus den GitHub-Commit-Betreffs
    eines Kunden im Zeitraum [from, to] — für die Rechnungs-Leistungsbeschreibung.
    Owner-gescopt: fremde Kunden → 404."""
    customer = await db.get(Customer, customer_id)  # scoped → None if not owned
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    if not settings.GITHUB_TOKEN or not customer.github_repos:
        return {"summary": None, "commit_count": 0, "themes": []}

    import json as _json
    try:
        parsed = _json.loads(customer.github_repos)
        repos = parsed if isinstance(parsed, list) else [customer.github_repos]
    except (_json.JSONDecodeError, TypeError):
        repos = [r.strip() for r in customer.github_repos.split(",") if r.strip()]

    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    subjects: list[str] = []
    async with httpx.AsyncClient(timeout=10) as client:
        for repo in repos:
            repo = str(repo).strip().strip("/")
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{repo}/commits",
                    headers=headers,
                    params={"since": f"{from_}T00:00:00Z", "until": f"{to}T23:59:59Z", "per_page": 100},
                )
                if resp.status_code == 200:
                    for c in resp.json():
                        subj = c["commit"]["message"].split("\n")[0].strip()
                        # Skip merge/co-author noise lines
                        if subj and not subj.lower().startswith("merge "):
                            subjects.append(subj)
            except Exception:
                continue

    if not subjects:
        return {"summary": None, "commit_count": 0, "themes": []}

    # Group by theme, count, order by frequency (biggest efforts first), dedupe.
    counts: dict[str, int] = {}
    order: list[str] = []
    for s in subjects:
        t = _commit_theme(s)
        if t not in counts:
            order.append(t)
        counts[t] = counts.get(t, 0) + 1
    # Sort: maintenance bucket last, otherwise by frequency desc then first-seen.
    themes = sorted(
        order,
        key=lambda t: (t == _MAINT_LABEL, -counts[t], order.index(t)),
    )
    capped = themes[:8]
    more = len(themes) - len(capped)

    bullet_lines = "\n".join(f"• {t}" for t in capped)
    if more > 0:
        bullet_lines += f"\n• u. a. ({more} weitere Bereiche)"
    summary = f"{_SUMMARY_MARKER}{from_} – {to}):\n{bullet_lines}"

    return {
        "summary": summary,
        "commit_count": len(subjects),
        "themes": capped,
    }
