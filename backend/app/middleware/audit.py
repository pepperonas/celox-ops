"""Audit middleware: logs all mutating requests (POST/PUT/PATCH/DELETE) to audit_log."""
import logging
import re
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import async_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Skip noisy / non-business endpoints
SKIP_PATHS = ("/api/auth/login", "/api/health")
# Extract entity type + id from URL like /api/invoices/{uuid}
ENTITY_PATTERN = re.compile(r"^/api/([a-z-]+)(?:/([0-9a-f-]{8,}|[^/]+))?")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)

        if (
            request.method not in MUTATING_METHODS
            or request.url.path in SKIP_PATHS
            or not request.url.path.startswith("/api/")
        ):
            return response

        # Invalidate the dashboard stats cache after any successful mutation
        # (cheap — just resets an in-memory dict). Without this, marking an
        # invoice paid leaves the dashboard showing it as overdue for up to 60s.
        if 200 <= response.status_code < 400 and not request.url.path.startswith("/api/dashboard"):
            try:
                from app.routers.dashboard import invalidate_stats_cache
                invalidate_stats_cache()
            except Exception as e:  # pragma: no cover — never break the response
                logger.warning(f"Stats-Cache-Invalidierung fehlgeschlagen: {e}")

        # Best-effort logging — never block / break the response
        try:
            # Reconstruct user from JWT (already validated by route)
            user = "anonymous"
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                from app.auth import verify_token
                try:
                    payload = verify_token(auth.split(" ", 1)[1])
                    user = payload.get("sub", "unknown")
                except Exception:
                    user = "invalid-token"

            entity_type, entity_id = None, None
            m = ENTITY_PATTERN.match(request.url.path)
            if m:
                entity_type = m.group(1)
                entity_id = m.group(2)

            entry = AuditLog(
                user=user,
                action=request.method,
                path=request.url.path,
                entity_type=entity_type,
                entity_id=entity_id,
                status_code=response.status_code,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            async with async_session_factory() as session:
                session.add(entry)
                await session.commit()
        except Exception as e:
            logger.warning(f"Audit-Log fehlgeschlagen: {e}")

        return response
