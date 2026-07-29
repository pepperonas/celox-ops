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
    "/api/reference-values/rename",  # benennt Werte in allen Datensätzen um
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
    """Prüft zwei Dinge in EINEM Nutzer-Lookup:

    1. Destruktives für nicht-destruktive Rollen (Verbot, s. o.).
    2. Die Erlaubnisliste für zugeschnittene Rollen (`role_scope`, deny-by-default).

    Die zweite Prüfung braucht den Lookup bei **jedem** `/api/`-Request — anders
    als bei (1) reicht der Rollen-Claim aus dem Token hier nicht: Wer gerade zum
    Verkäufer herabgestuft wurde, behielte mit einem alten Token bis zu 24 h
    volle Rechte. Ein indizierter SELECT auf `username` pro Request ist der Preis
    dafür; `get_current_user` macht ohnehin schon einen.
    """

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        path = request.url.path
        method = request.method
        destructive = is_destructive(method, path)
        # Für die Erlaubnisliste interessiert jeder API-Aufruf. CORS-Preflights
        # tragen keinen Authorization-Header und müssen durch.
        relevant = destructive or (path.startswith("/api/") and method != "OPTIONS")
        if not relevant:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)   # unauthentifiziert → Auth-Kette antwortet

        from sqlalchemy import select

        from app.auth import verify_token
        from app.database import async_session_factory
        from app.middleware.role_scope import DENY_MESSAGE as SCOPE_DENY
        from app.middleware.role_scope import allowed_for_role
        from app.models.user import NON_DESTRUCTIVE_ROLES, User

        # Token unlesbar/abgelaufen → durchlassen; die Auth-Kette der Route
        # antwortet gleich mit 401. Hier zusätzlich 403 zu senden würde einen
        # abgelaufenen Login als Rechteproblem darstellen.
        try:
            payload = verify_token(auth.split(" ", 1)[1])
        except Exception:
            logger.debug("Token unlesbar — Rollenprüfung übersprungen", exc_info=True)
            return await call_next(request)
        username = payload.get("sub")
        if not username:
            return await call_next(request)

        # Der Lookup selbst darf NICHT fail-open sein. Kann die Rolle nicht
        # festgestellt werden (DB weg, Verbindungsfehler), wäre ein Durchlassen
        # eine stille Rechteausweitung: ein Verkäufer bekäme die ganze App.
        # Deshalb 503 statt „weiter" — ehrlich und geschlossen.
        try:
            async with async_session_factory() as session:
                user = (
                    await session.execute(select(User).where(User.username == username))
                ).scalar_one_or_none()
        except Exception:
            logger.exception("Rollenprüfung nicht möglich — Request abgewiesen: %s %s",
                             method, path)
            return JSONResponse(
                status_code=503,
                content={"detail": "Rechteprüfung derzeit nicht möglich. Bitte erneut versuchen."},
            )

        if user is None:
            return await call_next(request)   # unbekannter Nutzer → 401 von der Route

        role_value = getattr(user.role, "value", user.role)

        if not allowed_for_role(role_value, method, path):
            logger.info(
                "Ausserhalb des Rollen-Zuschnitts blockiert: %s %s (Nutzer %s, Rolle %s)",
                method, path, username, role_value,
            )
            return JSONResponse(status_code=403, content={"detail": SCOPE_DENY})

        if destructive and user.role in NON_DESTRUCTIVE_ROLES:
            logger.info(
                "Destruktive Aktion blockiert: %s %s (Nutzer %s, Rolle %s)",
                method, path, username, role_value,
            )
            return JSONResponse(status_code=403, content={"detail": DENY_MESSAGE})

        return await call_next(request)
