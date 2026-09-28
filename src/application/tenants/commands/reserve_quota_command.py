"""Reserve quota command and handler for transactional tenant budget reservation."""

from dataclasses import dataclass
from decimal import Decimal

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class ReserveQuotaCommand:
    """Command DTO to request atomic budget reservation for an inference."""

    tenant_id: str
    estimated_cost: Decimal
    model_id: str


@dataclass(frozen=True)
class ReserveQuotaResult:
    """Result DTO returned upon successful budget reservation."""

    tenant_id: str
    reserved_amount: Decimal
    remaining_balance: Decimal
    model_id: str


class ReserveQuotaCommandHandler:
    """Application use case for processing tenant quota reservations."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def handle(self, command: ReserveQuotaCommand) -> ReserveQuotaResult:
        tenant_vo = TenantId(command.tenant_id)
        with self._unit_of_work as uow:
            tenant = uow.tenants.get_for_update(tenant_vo)
            if tenant is None:
                raise ValueError(f"Tenant '{command.tenant_id}' no encontrado.")

            tenant.reserve_budget(
                estimated_cost=command.estimated_cost,
                model_id=command.model_id,
            )

            uow.tenants.add(tenant)
            uow.commit()

            return ReserveQuotaResult(
                tenant_id=str(tenant.id),
                reserved_amount=command.estimated_cost,
                remaining_balance=tenant.budget.available_balance,
                model_id=command.model_id,
            )
