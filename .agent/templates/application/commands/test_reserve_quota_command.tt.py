"""Test template canónico para ReserveQuotaCommandHandler."""

from decimal import Decimal
from typing import Optional
import pytest
from src.domain.tenants.entities.tenant_entity import Tenant
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from .reserve_quota_command import ReserveQuotaCommand, ReserveQuotaCommandHandler


class FakeTenantRepo:
    def __init__(self) -> None:
        self.tenants: dict[str, Tenant] = {}

    def get_for_update(self, tenant_id: TenantId) -> Optional[Tenant]:
        return self.tenants.get(str(tenant_id))

    def add(self, tenant: Tenant) -> None:
        self.tenants[str(tenant.id)] = tenant


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.tenants = FakeTenantRepo()
        self.committed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def test_reserve_quota_handler_success() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("corp-1")
    tenant = Tenant(tenant_id=tid, name="Corp 1", budget=MonetaryBudget(balance=Decimal("50.00")))
    uow.tenants.add(tenant)

    handler = ReserveQuotaCommandHandler(unit_of_work=uow)  # type: ignore[arg-type]
    cmd = ReserveQuotaCommand(tenant_id="corp-1", estimated_cost=Decimal("10.00"), model_id="gpt-4o-mini")

    result = handler.handle(cmd)

    assert result.tenant_id == "corp-1"
    assert result.reserved_amount == Decimal("10.00")
    assert result.remaining_balance == Decimal("40.00")
    assert uow.committed is True


def test_reserve_quota_handler_tenant_not_found_raises_error() -> None:
    uow = FakeUnitOfWork()
    handler = ReserveQuotaCommandHandler(unit_of_work=uow)  # type: ignore[arg-type]
    cmd = ReserveQuotaCommand(tenant_id="non-existent", estimated_cost=Decimal("1.00"), model_id="gpt-4o-mini")

    with pytest.raises(ValueError, match="no encontrado"):
        handler.handle(cmd)
