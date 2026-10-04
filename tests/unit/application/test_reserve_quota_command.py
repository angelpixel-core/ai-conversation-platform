"""Unit tests for ReserveQuotaCommand and ReserveQuotaCommandHandler."""

from decimal import Decimal
from typing import Self

import pytest

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommand,
    ReserveQuotaCommandHandler,
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


class FakeUnitOfWork(UnitOfWorkPort):
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


def test_reserve_quota_handler_success() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("corp-1")
    tenant = Tenant(tenant_id=tid, name="Corp 1", budget=MonetaryBudget(balance=Decimal("50.00")))
    uow.tenants.add(tenant)

    handler = ReserveQuotaCommandHandler(unit_of_work=uow)
    cmd = ReserveQuotaCommand(
        tenant_id="corp-1",
        estimated_cost=Decimal("10.00"),
        model_id="gpt-4o-mini",
    )

    result = handler.handle(cmd)

    assert result.tenant_id == "corp-1"
    assert result.reserved_amount == Decimal("10.00")
    assert result.remaining_balance == Decimal("40.00")
    assert result.model_id == "gpt-4o-mini"
    assert uow.committed is True


def test_reserve_quota_handler_tenant_not_found_raises_error() -> None:
    uow = FakeUnitOfWork()
    handler = ReserveQuotaCommandHandler(unit_of_work=uow)
    cmd = ReserveQuotaCommand(
        tenant_id="non-existent",
        estimated_cost=Decimal("1.00"),
        model_id="gpt-4o-mini",
    )

    with pytest.raises(ValueError, match="no encontrado"):
        handler.handle(cmd)


def test_reserve_quota_handler_exceeded_quota_raises_error() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("corp-1")
    tenant = Tenant(tenant_id=tid, name="Corp 1", budget=MonetaryBudget(balance=Decimal("5.00")))
    uow.tenants.add(tenant)

    handler = ReserveQuotaCommandHandler(unit_of_work=uow)
    cmd = ReserveQuotaCommand(
        tenant_id="corp-1",
        estimated_cost=Decimal("10.00"),
        model_id="gpt-4o-mini",
    )

    with pytest.raises(ValueError, match="Cuota excedida"):
        handler.handle(cmd)
