"""Tenant dependencies for FastAPI endpoints."""

from typing import Annotated

from fastapi import Header, HTTPException, status

from src.application.shared.tenancy.tenant_context import get_current_tenant_id


def get_current_tenant_id_dep() -> str:
    """Extract active tenant_id from context, raising HTTP 400 if unavailable."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contexto de inquilino no disponible. Se requiere cabecera 'X-Tenant-ID'.",
        )
    return tenant_id


def get_optional_tenant_id_dep(
    x_tenant_id: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract tenant_id optionally from context or fallback to header."""
    return get_current_tenant_id() or (x_tenant_id.strip() if x_tenant_id else None)
