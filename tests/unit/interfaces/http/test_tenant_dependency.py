"""Unit tests for tenant dependencies in FastAPI."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.application.shared.tenancy.tenant_context import tenant_context
from src.interfaces.http.dependencies.tenant_dependency import (
    get_current_tenant_id_dep,
    get_optional_tenant_id_dep,
)


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


def test_optional_tenant_dependency() -> None:
    app = FastAPI()

    @app.get("/public-or-private")
    def get_mixed(
        tenant_id: str | None = Depends(get_optional_tenant_id_dep),
    ) -> dict[str, str | None]:
        return {"tenant_id": tenant_id}

    client = TestClient(app)

    # 1. No context, no header
    res1 = client.get("/public-or-private")
    assert res1.status_code == 200
    assert res1.json() == {"tenant_id": None}

    # 2. Header provided
    res2 = client.get("/public-or-private", headers={"X-Tenant-ID": "header-tenant"})
    assert res2.status_code == 200
    assert res2.json() == {"tenant_id": "header-tenant"}
