"""Integration tests for budget exceeded rejection (HTTP 402 Payment Required)."""

from decimal import Decimal

from fastapi.testclient import TestClient

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


def test_budget_exceeded_rejection_http_402() -> None:
    uow = InMemoryUnitOfWork()
    tenant = Tenant(
        tenant_id=TenantId("broke-startup"),
        name="Broke Startup",
        budget=MonetaryBudget(balance=Decimal("0.00"), reserved_amount=Decimal("0.00")),
        policy=TenantPolicy(allowed_models=frozenset({"gpt-4o-mini"})),
    )
    uow.tenants.add(tenant)

    app = build_api(unit_of_work=uow, enable_tenant_middleware=True)
    client = TestClient(app)

    # Calling an endpoint or quota reservation when balance is insufficient returns 402
    response = client.post(
        "/admin/tenants/broke-startup/reserve",
        json={"estimated_cost": "5.00", "model_id": "gpt-4o-mini"},
        headers={"X-Tenant-ID": "broke-startup"},
    )
    assert response.status_code == 402
    data = response.json()
    assert "detail" in data
    assert (
        "presupuesto" in data["detail"].lower()
        or "quota" in data["detail"].lower()
        or "saldo" in data["detail"].lower()
    )
