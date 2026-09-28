"""Test template canónico para dependencias FastAPI de Tenancy."""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from src.application.shared.tenancy.tenant_context import tenant_context
from .tenant_dependency import get_current_tenant_id_dep, get_optional_tenant_id_dep


def test_tenant_dependency_returns_active_context() -> None:
    app = FastAPI()

    @app.get("/items")
    def get_items(tenant_id: str = Depends(get_current_tenant_id_dep)) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    client = TestClient(app)

    with tenant_context("corp-100"):
        response = client.get("/items")
        assert response.status_code == 200
        assert response.json() == {"tenant_id": "corp-100"}


def test_tenant_dependency_raises_400_when_none() -> None:
    app = FastAPI()

    @app.get("/items")
    def get_items(tenant_id: str = Depends(get_current_tenant_id_dep)) -> dict[str, str]:
        return {"tenant_id": tenant_id}

    client = TestClient(app)
    response = client.get("/items")
    assert response.status_code == 400
    assert "Contexto de inquilino no disponible" in response.json()["detail"]
