"""Template canónico para el Comando y Handler ReserveQuotaCommand (CQRS).

Reglas:
- Pertenece a la capa de Aplicación (src/application/tenants/commands/).
- DTO inmutable (frozen dataclass).
- Handler coordina la reserva transaccional atómica bajo la Unidad de Trabajo (UnitOfWork).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class ReserveQuotaCommand:
    """Command DTO para solicitar reserva atómica de saldo para una inferencia."""

    tenant_id: str
    estimated_cost: Decimal
    model_id: str


@dataclass(frozen=True)
class ReserveQuotaResult:
    """Resultado devuelto tras una reserva exitosa."""

    tenant_id: str
    reserved_amount: Decimal
    remaining_balance: Decimal
    model_id: str


class ReserveQuotaCommandHandler:
    """Caso de uso de aplicación para procesar reservas de cuota de inquilinos."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def handle(self, command: ReserveQuotaCommand) -> ReserveQuotaResult:
        tenant_vo = TenantId(command.tenant_id)
        with self._unit_of_work as uow:
            # Obtener con bloqueo pesimista en el repositorio
            tenants_repo: Any = getattr(uow, "tenants", None)
            if tenants_repo is None:
                raise RuntimeError("El repositorio de tenants no está configurado en UnitOfWork.")

            tenant = tenants_repo.get_for_update(tenant_vo)
            if tenant is None:
                raise ValueError(f"Tenant '{command.tenant_id}' no encontrado.")

            # Aplicar invariante de dominio
            tenant.reserve_budget(
                estimated_cost=command.estimated_cost,
                model_id=command.model_id,
            )

            tenants_repo.add(tenant)
            uow.commit()

            return ReserveQuotaResult(
                tenant_id=str(tenant.id),
                reserved_amount=command.estimated_cost,
                remaining_balance=tenant.budget.available_balance,
                model_id=command.model_id,
            )
