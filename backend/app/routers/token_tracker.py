import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.config import settings

router = APIRouter(
    prefix="/api/token-tracker",
    tags=["token-tracker"],
    dependencies=[Depends(get_current_user)],
)


class ShareCreate(BaseModel):
    project: str
    label: str | None = None
    expires_in_days: int | None = None


def _tracker_headers() -> dict:
    return {"Authorization": f"Bearer {settings.TOKEN_TRACKER_ADMIN_KEY}"}


def _tracker_url(path: str) -> str:
    return f"{settings.TOKEN_TRACKER_BASE_URL}{path}"


@router.get("/projects")
async def list_projects() -> list:
    """Verfügbare Projekte im Token Tracker."""
    if not settings.TOKEN_TRACKER_BASE_URL:
        raise HTTPException(status_code=503, detail="Token Tracker nicht konfiguriert")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_tracker_url("/api/shares/projects"), headers=_tracker_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Token Tracker Fehler")
    return resp.json()


@router.get("/shares")
async def list_shares() -> list:
    """Alle aktiven Shares."""
    if not settings.TOKEN_TRACKER_BASE_URL:
        raise HTTPException(status_code=503, detail="Token Tracker nicht konfiguriert")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_tracker_url("/api/shares"), headers=_tracker_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Token Tracker Fehler")
    return resp.json()


@router.post("/shares")
async def create_share(data: ShareCreate) -> dict:
    """Neuen Share-Token erstellen."""
    if not settings.TOKEN_TRACKER_BASE_URL:
        raise HTTPException(status_code=503, detail="Token Tracker nicht konfiguriert")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            _tracker_url("/api/shares"),
            headers=_tracker_headers(),
            json=data.model_dump(exclude_none=True),
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail="Token Tracker Fehler")
    share = resp.json()
    # Return full public URL
    share["public_url"] = f"{settings.TOKEN_TRACKER_BASE_URL.replace('http://localhost:3007', 'https://tracker.celox.io')}/api/public/share/{share['id']}"
    return share


@router.delete("/shares/{share_id}")
async def delete_share(share_id: str) -> None:
    """Share-Token löschen."""
    if not settings.TOKEN_TRACKER_BASE_URL:
        raise HTTPException(status_code=503, detail="Token Tracker nicht konfiguriert")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(_tracker_url(f"/api/shares/{share_id}"), headers=_tracker_headers())
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=resp.status_code, detail="Token Tracker Fehler")
