"""Unit tests for SettleQuotaCommand and SettleQuotaCommandHandler."""

from decimal import Decimal
from typing import Self

import pytest

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.application.tenants.commands.settle_quota_command import (
    SettleQuotaCommand,
    SettleQuotaCommandHandler,
)
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeTenantRepo(TenantRepositoryPort):
    def __init__(self) -> None:
        self.tenants: dict[str, Tenant] = {}

    def get(self, tenant_id: TenantId) -> Tenant | None:
        return self.tenants.get(str(tenant_id))

    def get_for_update(self, tenant_id: TenantId) -> Tenant | None:
        return self.get(tenant_id)

    def add(self, tenant: Tenant) -> None:
        self.tenants[str(tenant.id)] = tenant

    def list(self) -> list[Tenant]:
        return list(self.tenants.values())


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.tenants = FakeTenantRepo()
        self.committed = False
        self.conversations = None  # type: ignore[assignment]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def test_settle_quota_handler_success() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("corp-1")
    tenant = Tenant(tenant_id=tid, name="Corp 1", budget=MonetaryBudget(balance=Decimal("50.00")))
    tenant.reserve_budget(estimated_cost=Decimal("10.00"), model_id="gpt-4o-mini")
    uow.tenants.add(tenant)

    handler = SettleQuotaCommandHandler(unit_of_work=uow)
    cmd = SettleQuotaCommand(
        tenant_id="corp-1",
        reserved_cost=Decimal("10.00"),
        actual_cost=Decimal("7.50"),
    )

    result = handler.handle(cmd)

    assert result.tenant_id == "corp-1"
    assert result.actual_cost == Decimal("7.50")
    assert result.new_balance == Decimal("42.50")
    assert uow.committed is True


def test_settle_quota_handler_tenant_not_found_raises_error() -> None:
    uow = FakeUnitOfWork()
    handler = SettleQuotaCommandHandler(unit_of_work=uow)
    cmd = SettleQuotaCommand(
        tenant_id="non-existent",
        reserved_cost=Decimal("10.00"),
        actual_cost=Decimal("7.50"),
    )

    with pytest.raises(ValueError, match="no encontrado"):
        handler.handle(cmd)
