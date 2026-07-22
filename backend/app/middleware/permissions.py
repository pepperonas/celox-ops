"""Sperrt destruktive Aktionen für nicht-destruktive Rollen (z. B. `mitarbeiter`).

Bewusst als Middleware statt als Dependency pro Route: so kann keine bestehende
oder künftige Route vergessen werden. Geprüft wird VOR dem Handler — es wird
also nichts gelöscht und dann zurückgerollt.

Zwei Ebenen:
1. Jedes `DELETE` auf `/api/*` (deckt Kunden, Leads, Rechnungen, To-dos … ab).
2. Eine Denylist für destruktive Nicht-DELETE-Routen (Merge löscht Leads per POST).

Die Rolle wird gegen die DB geprüft, nicht gegen einen JWT-Claim: sonst würde
eine Herabstufung erst gelten, wenn das alte Token abläuft (bis 24 h).
Destruktive Requests sind selten — die Zusatzabfrage fällt nicht ins Gewicht.
"""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Destruktive Endpunkte, die NICHT DELETE benutzen (Merge löscht Leads per POST).
# Beim Anlegen neuer destruktiver POST-Routen hier ergänzen.
DESTRUCTIVE_POST_PATHS = (
    "/api/rainmaker/duplicates/merge",
    "/api/rainmaker/duplicates/merge-batch",
)

DENY_MESSAGE = (
    "Diese Aktion ist für die Rolle „Mitarbeiter“ gesperrt — "
    "bitte wende dich an den Kontoinhaber."
)


def is_destructive(method: str, path: str) -> bool:
    """Rein + testbar: Ist dieser Request destruktiv?"""
    if method == "DELETE" and path.startswith("/api/"):
        return True
    return method == "POST" and path.rstrip("/") in DESTRUCTIVE_POST_PATHS


class PermissionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        if not is_destructive(request.method, request.url.path):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)   # unauthentifiziert → Auth-Kette antwortet

        try:
            from sqlalchemy import select

            from app.auth import verify_token
            from app.database import async_session_factory
            from app.models.user import NON_DESTRUCTIVE_ROLES, User

            payload = verify_token(auth.split(" ", 1)[1])
            username = payload.get("sub")
            if not username:
                return await call_next(request)

            async with async_session_factory() as session:
                user = (
                    await session.execute(select(User).where(User.username == username))
                ).scalar_one_or_none()

            if user and user.role in NON_DESTRUCTIVE_ROLES:
                logger.info(
                    "Destruktive Aktion blockiert: %s %s (Nutzer %s, Rolle %s)",
                    request.method, request.url.path, username,
                    getattr(user.role, "value", user.role),
                )
                return JSONResponse(status_code=403, content={"detail": DENY_MESSAGE})
        except Exception:
            # Ungültiges Token o. Ä. — die reguläre Auth-Kette der Route
            # antwortet gleich mit 401; hier nicht zusätzlich blockieren.
            logger.debug("Rollenprüfung übersprungen", exc_info=True)

        return await call_next(request)
