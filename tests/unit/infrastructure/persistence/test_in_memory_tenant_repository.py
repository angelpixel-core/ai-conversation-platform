"""Unit tests for InMemoryTenantRepositoryAdapter."""

from decimal import Decimal

from src.infrastructure.persistence.in_memory.tenant_repository import (
    InMemoryTenantRepositoryAdapter,
)

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_in_memory_tenant_repository_satisfies_port() -> None:
    repo = InMemoryTenantRepositoryAdapter()
    assert isinstance(repo, TenantRepositoryPort)


def test_in_memory_tenant_repository_add_and_get() -> None:
    repo = InMemoryTenantRepositoryAdapter()
    tenant = Tenant(
        tenant_id=TenantId("tenant-mem-1"),
        name="Memory Tenant",
        budget=MonetaryBudget(balance=Decimal("300.00")),
    )
    repo.add(tenant)

    retrieved = repo.get(TenantId("tenant-mem-1"))
    assert retrieved is not None
    assert retrieved.id.value == "tenant-mem-1"
    assert retrieved.name == "Memory Tenant"
    assert retrieved.budget.balance == Decimal("300.00")


def test_in_memory_tenant_repository_get_not_found() -> None:
    repo = InMemoryTenantRepositoryAdapter()
    assert repo.get(TenantId("nonexistent")) is None
    assert repo.get_for_update(TenantId("nonexistent")) is None


def test_in_memory_tenant_repository_get_for_update() -> None:
    repo = InMemoryTenantRepositoryAdapter()
    tenant = Tenant(
        tenant_id=TenantId("tenant-lock"),
        name="Lock Tenant",
        budget=MonetaryBudget(balance=Decimal("150.00")),
    )
    repo.add(tenant)

    locked = repo.get_for_update(TenantId("tenant-lock"))
    assert locked is not None
    assert locked.id.value == "tenant-lock"


def test_in_memory_tenant_repository_list() -> None:
    repo = InMemoryTenantRepositoryAdapter()
    t1 = Tenant(
        tenant_id=TenantId("t-1"), name="T1", budget=MonetaryBudget(balance=Decimal("10.00"))
    )
    t2 = Tenant(
        tenant_id=TenantId("t-2"), name="T2", budget=MonetaryBudget(balance=Decimal("20.00"))
    )
    repo.add(t1)
    repo.add(t2)

    tenants = repo.list()
    assert len(tenants) == 2
    ids = {t.id.value for t in tenants}
    assert ids == {"t-1", "t-2"}
