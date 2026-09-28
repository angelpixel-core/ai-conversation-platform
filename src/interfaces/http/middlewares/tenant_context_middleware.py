"""TenantContextMiddleware for FastAPI ASGI applications."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.application.shared.tenancy.tenant_context import async_tenant_context

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware to capture and propagate active TenantContext across requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 1. Bypass public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # 2. Extract tenant ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id or not tenant_id.strip():
            if request.url.path.startswith("/admin"):
                return await call_next(request)
            return JSONResponse(
                status_code=400,
                content={
                    "detail": (
                        "Encabezado 'X-Tenant-ID' es obligatorio para "
                        "acceder a recursos protegidos."
                    )
                },
            )

        # 3. Propagate in execution context
        async with async_tenant_context(tenant_id.strip()):
            response = await call_next(request)
            return response
