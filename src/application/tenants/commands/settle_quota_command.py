"""Settle quota command and handler for reconciling final inference token costs."""

from dataclasses import dataclass
from decimal import Decimal

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class SettleQuotaCommand:
    """Command DTO to settle actual costs against previously reserved budget."""

    tenant_id: str
    reserved_cost: Decimal
    actual_cost: Decimal


@dataclass(frozen=True)
class SettleQuotaResult:
    """Result DTO returned upon successful cost settlement."""

    tenant_id: str
    actual_cost: Decimal
    new_balance: Decimal


class SettleQuotaCommandHandler:
    """Application use case for reconciling and settling tenant inference costs."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def handle(self, command: SettleQuotaCommand) -> SettleQuotaResult:
        tenant_vo = TenantId(command.tenant_id)
        with self._unit_of_work as uow:
            tenant = uow.tenants.get_for_update(tenant_vo)
            if tenant is None:
                raise ValueError(f"Tenant '{command.tenant_id}' no encontrado.")

            tenant.settle_actual_cost(
                reserved_cost=command.reserved_cost,
                actual_cost=command.actual_cost,
            )

            uow.tenants.add(tenant)
            uow.commit()

            return SettleQuotaResult(
                tenant_id=str(tenant.id),
                actual_cost=command.actual_cost,
                new_balance=tenant.budget.balance,
            )
