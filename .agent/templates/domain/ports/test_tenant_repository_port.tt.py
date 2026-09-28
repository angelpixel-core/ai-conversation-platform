"""Test template canónico para TenantRepositoryPort (validación de contrato)."""

from typing import List, Optional
from decimal import Decimal
import pytest
from ..value_objects.tenant_id import TenantId
from ..value_objects.monetary_budget import MonetaryBudget
from ..entities.tenant_entity import Tenant
from .tenant_repository_port import TenantRepositoryPort


class FakeTenantRepository(TenantRepositoryPort):
    """Implementación de prueba para verificar el contrato del puerto."""

    def __init__(self) -> None:
        self.storage: dict[str, Tenant] = {}

    def add(self, tenant: Tenant) -> None:
        self.storage[str(tenant.id)] = tenant

    def get(self, tenant_id: TenantId) -> Optional[Tenant]:
        return self.storage.get(str(tenant_id))

    def get_for_update(self, tenant_id: TenantId) -> Optional[Tenant]:
        return self.get(tenant_id)

    def list(self) -> List[Tenant]:
        return list(self.storage.values())


def test_tenant_repository_contract_add_and_get() -> None:
    repo = FakeTenantRepository()
    tid = TenantId("acme-inc")
    tenant = Tenant(tenant_id=tid, name="Acme", budget=MonetaryBudget(balance=Decimal("100.00")))

    repo.add(tenant)
    fetched = repo.get(tid)

    assert fetched is not None
    assert fetched.id == tid
    assert fetched.name == "Acme"


def test_tenant_repository_contract_not_found_returns_none() -> None:
    repo = FakeTenantRepository()
    assert repo.get(TenantId("missing-tenant")) is None


def test_tenant_repository_contract_list() -> None:
    repo = FakeTenantRepository()
    repo.add(Tenant(tenant_id=TenantId("t-1"), name="Tenant 1", budget=MonetaryBudget(balance=Decimal("10"))))
    repo.add(Tenant(tenant_id=TenantId("t-2"), name="Tenant 2", budget=MonetaryBudget(balance=Decimal("20"))))

    tenants = repo.list()
    assert len(tenants) == 2
