import time

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.config import settings

router = APIRouter(
    prefix="/api/github",
    tags=["github"],
    dependencies=[Depends(get_current_user)],
)

# Cache: 10 min TTL
_cache: dict = {"data": None, "time": 0}
CACHE_TTL = 600


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
