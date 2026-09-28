"""Unit tests for TenantContextMiddleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.interfaces.http.middlewares.tenant_context_middleware import (
    TenantContextMiddleware,
)


def test_tenant_middleware_allows_public_paths() -> None:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tenant_middleware_rejects_missing_header_on_protected_routes() -> None:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)

    @app.get("/conversations")
    def list_conv() -> list[str]:
        return []

    client = TestClient(app)
    response = client.get("/conversations")
    assert response.status_code == 400
    assert "X-Tenant-ID" in response.json()["detail"]


def test_tenant_middleware_sets_context_and_cleans_up() -> None:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)

    captured_tenant: list[str | None] = []

    @app.get("/conversations")
    def get_conv() -> dict[str, str | None]:
        captured = get_current_tenant_id()
        captured_tenant.append(captured)
        return {"tenant": captured}

    client = TestClient(app)
    response = client.get("/conversations", headers={"X-Tenant-ID": "tenant-corp-42"})
    assert response.status_code == 200
    assert response.json() == {"tenant": "tenant-corp-42"}
    assert captured_tenant == ["tenant-corp-42"]
    # Ensure execution context is cleared after request completes
    assert get_current_tenant_id() is None
