"""Integration tests for TenantAdminRouter endpoints (/admin/tenants) with RFC-32 contract."""

from fastapi.testclient import TestClient

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter
from src.interfaces.http.api import build_api


def test_tenant_admin_provision_and_list_rfc32() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    app = build_api(unit_of_work=uow)
    client = TestClient(app)

    # 1. Provision a tenant via POST /admin/tenants using canonical 'id'
    resp_create = client.post(
        "/admin/tenants",
        json={
            "id": "tenant-corp",
            "name": "Corporate Tech",
            "balance_usd": "500.00",
            "tier": "STANDARD",
            "monthly_budget_usd": "250.00",
            "contact_email": "ops@corptech.com",
            "allowed_models": ["gpt-4o", "gpt-4o-mini"],
        },
    )
    assert resp_create.status_code == 201
    created_data = resp_create.json()
    assert created_data["id"] == "tenant-corp"
    assert created_data["tenant_id"] == "tenant-corp"
    assert created_data["balance"] == "500.0000"

    # 2. Provision another tenant using alias 'tenant_id' (Tolerant Reader fallback)
    resp_create_alias = client.post(
        "/admin/tenants",
        json={
            "tenant_id": "tenant-globex",
            "name": "Globex Industries",
            "balance_usd": "1000.00",
            "tier": "PRO",
            "monthly_budget_usd": "2000.00",
            "contact_email": "admin@globex.com",
        },
    )
    assert resp_create_alias.status_code == 201
    alias_data = resp_create_alias.json()
    assert alias_data["id"] == "tenant-globex"
    assert alias_data["tenant_id"] == "tenant-globex"

    # 3. Duplicate provisioning returns 409 Conflict
    resp_dup = client.post(
        "/admin/tenants",
        json={
            "id": "tenant-corp",
            "name": "Corporate Tech",
        },
    )
    assert resp_dup.status_code == 409

    # 4. List tenants via GET /admin/tenants with RFC-32 structured format
    resp_list = client.get("/admin/tenants")
    assert resp_list.status_code == 200
    tenants_list = resp_list.json()
    assert len(tenants_list) == 2

    corp = next(t for t in tenants_list if t["id"] == "tenant-corp")
    assert corp["tenant_id"] == "tenant-corp"
    assert corp["name"] == "Corporate Tech"
    assert corp["status"] == "ACTIVE"
    assert corp["tier"] == "STANDARD"

    # Flattened backwards-compatibility fields
    assert corp["balance"] == "500.0000"
    assert corp["reserved_amount"] == "0.0000"
    assert corp["available_balance"] == "500.0000"
    assert corp["currency"] == "USD"

    # Structured RFC-32 sub-objects
    assert corp["financials"]["currency"] == "USD"
    assert corp["financials"]["balance"] == "500.0000"
    assert corp["financials"]["monthly_budget_usd"] == "250.0000"

    assert corp["limits"]["max_tokens_per_request"] == 4096
    assert corp["limits"]["max_requests_per_minute"] == 60

    assert corp["metadata"]["contact_email"] == "ops@corptech.com"
    assert "T" in corp["metadata"]["created_at"]

    # 5. Check budget via GET /admin/tenants/{id}/budget
    resp_budget = client.get("/admin/tenants/tenant-corp/budget")
    assert resp_budget.status_code == 200
    budget_data = resp_budget.json()
    assert budget_data["id"] == "tenant-corp"
    assert budget_data["tenant_id"] == "tenant-corp"
    assert budget_data["balance"] == "500.0000"

    # 6. Update policy via PATCH /admin/tenants/{id}/policy to PRO tier
    resp_policy = client.patch(
        "/admin/tenants/tenant-corp/policy",
        json={
            "tier": "PRO",
            "max_tokens_per_request": 8192,
            "monthly_budget_usd": "1500.00",
            "max_requests_per_minute": 120,
            "allowed_models": ["gpt-4o", "claude-3-5-sonnet", "o1-mini"],
        },
    )
    assert resp_policy.status_code == 200
    policy_data = resp_policy.json()
    assert policy_data["id"] == "tenant-corp"
    assert policy_data["tenant_id"] == "tenant-corp"
    assert policy_data["tier"] == "PRO"
    assert policy_data["max_tokens_per_request"] == 8192
    assert policy_data["max_requests_per_minute"] == 120
    assert "o1-mini" in policy_data["allowed_models"]

    # 7. Reserve quota via POST /admin/tenants/{id}/reserve
    resp_reserve = client.post(
        "/admin/tenants/tenant-corp/reserve",
        json={
            "estimated_cost": "10.00",
            "model_id": "gpt-4o",
        },
    )
    assert resp_reserve.status_code == 200
    reserve_data = resp_reserve.json()
    assert reserve_data["id"] == "tenant-corp"
    assert reserve_data["tenant_id"] == "tenant-corp"
    assert reserve_data["reserved_cost"] == "10.0000"
    assert reserve_data["remaining_balance"] == "490.0000"
