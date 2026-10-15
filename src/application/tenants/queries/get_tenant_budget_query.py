"""Get tenant budget query and handler for reading real-time balances."""

from dataclasses import dataclass
from decimal import Decimal

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.tenants.exceptions import TenantNotFoundError
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class TenantBudgetDTO:
    """Current token budget and balances for a tenant."""

    id: str
    tenant_id: str
    balance: Decimal
    reserved_amount: Decimal
    available_balance: Decimal
    currency: str


@dataclass(frozen=True)
class GetTenantBudgetQuery:
    """Query DTO requesting budget status for a given tenant."""

    tenant_id: str


class GetTenantBudgetQueryHandler:
    """Application use case for reading tenant budget and financial balances."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initialize the handler with a transactional UnitOfWork boundary.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, query: GetTenantBudgetQuery) -> TenantBudgetDTO:
        """Execute read query returning current budget state.

        Args:
            query: GetTenantBudgetQuery with target tenant_id.

        Returns:
            TenantBudgetDTO with current financial state.

        Raises:
            TenantNotFoundError: If tenant does not exist.
        """
        tenant_vo = TenantId(query.tenant_id)
        with self._unit_of_work as uow:
            tenant = uow.tenants.get(tenant_vo)
            if tenant is None:
                raise TenantNotFoundError(f"Tenant '{query.tenant_id}' no encontrado.")

            return TenantBudgetDTO(
                id=str(tenant.id),
                tenant_id=str(tenant.id),
                balance=tenant.budget.balance,
                reserved_amount=tenant.budget.reserved_amount,
                available_balance=tenant.budget.available_balance,
                currency=tenant.budget.currency,
            )


__all__ = [
    "GetTenantBudgetQuery",
    "GetTenantBudgetQueryHandler",
    "TenantBudgetDTO",
]
