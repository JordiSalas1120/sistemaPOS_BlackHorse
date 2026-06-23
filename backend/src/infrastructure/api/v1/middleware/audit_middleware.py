"""
Middleware de auditoría: registra en audit_logs toda petición mutante
(POST / PUT / DELETE / PATCH) con actor, IP, ruta, status code y duración.

No captura payloads before/after — eso lo hacen los use cases individualmente
con contexto de negocio. Este middleware es la red de seguridad para
operaciones que no tengan auditoría explícita.
"""
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.domain.models.audit_log import AuditLog
from src.domain.models.enums import AuditAction
from src.infrastructure.adapters.postgres_repo.audit_log_repository import AuditLogRepository
from src.infrastructure.database.connection import async_session_factory

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Rutas que excluimos (health checks, docs, openapi)
EXCLUDED_PREFIXES = ("/docs", "/redoc", "/openapi", "/health", "/")


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in EXCLUDED_PREFIXES if p != "/"):
            return await call_next(request)
        # Excluir exactamente "/"
        if path == "/":
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        # Solo auditar respuestas exitosas (2xx)
        if 200 <= response.status_code < 300:
            actor = request.headers.get("x-actor", "api")
            ip = request.client.host if request.client else "unknown"
            await self._log(
                method=request.method,
                path=path,
                status_code=response.status_code,
                actor=actor,
                ip=ip,
                duration_ms=duration_ms,
            )

        return response

    async def _log(
        self,
        method: str,
        path: str,
        status_code: int,
        actor: str,
        ip: str,
        duration_ms: int,
    ) -> None:
        try:
            async with async_session_factory() as session:
                repo = AuditLogRepository(session)
                await repo.create(AuditLog(
                    id=uuid.uuid4(),
                    entity_type="http_request",
                    entity_id=uuid.uuid4(),
                    action=AuditAction.UPDATE,
                    actor=actor,
                    ip_address=ip,
                    payload={
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                    created_at=datetime.now(timezone.utc),
                ))
                await session.commit()
        except Exception:
            # El middleware nunca debe romper el request principal
            pass
