"""Integration tests for TenantAdminRouter endpoints (/admin/tenants)."""

from fastapi.testclient import TestClient

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


def test_tenant_admin_provision_and_list() -> None:
    uow = InMemoryUnitOfWork()
    app = build_api(unit_of_work=uow)
    client = TestClient(app)

    # 1. Provision a tenant via POST /admin/tenants
    resp_create = client.post(
        "/admin/tenants",
        json={
            "id": "tenant-corp",
            "name": "Corporate Tech",
            "balance_usd": "500.00",
            "tier": "STANDARD",
            "monthly_budget_usd": "250.00",
            "allowed_models": ["gpt-4o", "gpt-4o-mini"],
        },
    )
    assert resp_create.status_code == 201
    created_data = resp_create.json()
    assert created_data["tenant_id"] == "tenant-corp"
    assert created_data["balance"] == "500.0000"

    # 2. Duplicate provisioning returns 409 Conflict
    resp_dup = client.post(
        "/admin/tenants",
        json={
            "id": "tenant-corp",
            "name": "Corporate Tech",
        },
    )
    assert resp_dup.status_code == 409

    # 3. List tenants via GET /admin/tenants
    resp_list = client.get("/admin/tenants")
    assert resp_list.status_code == 200
    tenants_list = resp_list.json()
    assert len(tenants_list) == 1
    assert tenants_list[0]["tenant_id"] == "tenant-corp"
    assert tenants_list[0]["name"] == "Corporate Tech"
    assert tenants_list[0]["tier"] == "STANDARD"

    # 4. Check budget via GET /admin/tenants/{id}/budget
    resp_budget = client.get("/admin/tenants/tenant-corp/budget")
    assert resp_budget.status_code == 200
    budget_data = resp_budget.json()
    assert budget_data["tenant_id"] == "tenant-corp"
    assert budget_data["balance"] == "500.0000"
