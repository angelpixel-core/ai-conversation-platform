"""Template canónico para TenantContextMiddleware en FastAPI.

Reglas:
- Pertenece a src/interfaces/http/middlewares/tenant_context_middleware.py.
- Extrae la cabecera 'X-Tenant-ID' de las peticiones HTTP entrantes.
- Enruta el ciclo de vida de la petición dentro de async_tenant_context().
- Omite rutas públicas (/health, /docs, /openapi.json).
"""

from collections.abc import Callable
from typing import Awaitable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.application.shared.tenancy.tenant_context import async_tenant_context

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware ASGI para captura y propagación contextual de inquilinos en FastAPI."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 1. Bypass para endpoints públicos de monitoreo y documentación
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # 2. Extracción de encabezado de inquilino
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id or not tenant_id.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Encabezado 'X-Tenant-ID' es obligatorio para acceder a recursos protegidos."
                },
            )

        # 3. Propagación en AnyIO contextvars
        async with async_tenant_context(tenant_id.strip()):
            response = await call_next(request)
            return response
