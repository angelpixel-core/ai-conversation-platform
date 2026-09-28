"""Integration tests for TenantContextMiddleware and Tenant Admin Router."""

from decimal import Decimal

from fastapi.testclient import TestClient

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


def test_tenant_middleware_enforcement_and_isolation() -> None:
    uow = InMemoryUnitOfWork()
    app = build_api(unit_of_work=uow, enable_tenant_middleware=True)
    client = TestClient(app)

    # 1. Missing header on protected path fails with 400
    res_no_header = client.get("/conversations")
    assert res_no_header.status_code == 400
    assert "X-Tenant-ID" in res_no_header.json()["detail"]

    # 2. Public path succeeds without header
    res_health = client.get("/health")
    assert res_health.status_code == 200


def test_tenant_admin_endpoints() -> None:
    uow = InMemoryUnitOfWork()
    tenant = Tenant(
        tenant_id=TenantId("corp-acme"),
        name="Acme Corporation",
        budget=MonetaryBudget(balance=Decimal("250.00"), reserved_amount=Decimal("15.00")),
        policy=TenantPolicy(
            tier=TenantTier.STANDARD,
            max_tokens_per_request=4096,
            monthly_budget_usd=Decimal("300.00"),
            allowed_models=frozenset({"gpt-4o-mini"}),
        ),
    )
    uow.tenants.add(tenant)

    app = build_api(unit_of_work=uow, enable_tenant_middleware=True)
    client = TestClient(app)

    # 1. GET /admin/tenants/{id}/budget
    res_budget = client.get("/admin/tenants/corp-acme/budget")
    assert res_budget.status_code == 200
    data = res_budget.json()
    assert data["tenant_id"] == "corp-acme"
    assert data["balance"] == "250.0000"
    assert data["reserved_amount"] == "15.0000"
    assert data["available_balance"] == "235.0000"

    # 2. PATCH /admin/tenants/{id}/policy
    patch_body = {
        "tier": "ENTERPRISE",
        "max_tokens_per_request": 8192,
        "monthly_budget_usd": "1000.00",
        "allowed_models": ["gpt-4o", "gemini-1.5-pro"],
    }
    res_patch = client.patch("/admin/tenants/corp-acme/policy", json=patch_body)
    assert res_patch.status_code == 200
    updated_policy_data = res_patch.json()
    assert updated_policy_data["tier"] == "ENTERPRISE"
    assert updated_policy_data["max_tokens_per_request"] == 8192
    assert "gpt-4o" in updated_policy_data["allowed_models"]

    # 3. GET nonexistent tenant budget returns 404
    res_not_found = client.get("/admin/tenants/nonexistent-corp/budget")
    assert res_not_found.status_code == 404
