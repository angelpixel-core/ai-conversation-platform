"""Template canónico para Dependencias de FastAPI para Inquilinos.

Reglas:
- Pertenece a src/interfaces/http/dependencies/tenant_dependency.py.
- Provee inyección de dependencias para endpoints que requieran el tenant_id activo.
- Lanza HTTPException 400 Bad Request si la ruta requiere tenant y este no fue establecido.
"""

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from src.application.shared.tenancy.tenant_context import get_current_tenant_id


def get_current_tenant_id_dep() -> str:
    """Extrae el tenant_id activo desde el TenantContext (inyectado por middleware)."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contexto de inquilino no disponible. Se requiere cabecera 'X-Tenant-ID'.",
        )
    return tenant_id


def get_optional_tenant_id_dep(
    x_tenant_id: Annotated[Optional[str], Header()] = None,
) -> Optional[str]:
    """Extrae el tenant_id de forma opcional (para endpoints mixtos o públicos)."""
    return get_current_tenant_id() or (x_tenant_id.strip() if x_tenant_id else None)
