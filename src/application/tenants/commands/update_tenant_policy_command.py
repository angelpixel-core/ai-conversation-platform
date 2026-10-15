"""Update tenant policy command and handler for governance changes."""

from dataclasses import dataclass
from decimal import Decimal

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.exceptions import TenantNotFoundError
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class UpdateTenantPolicyCommand:
    """Command DTO requesting update to tenant governance policy."""

    tenant_id: str
    tier: str | None = None
    max_tokens_per_request: int | None = None
    monthly_budget_usd: Decimal | None = None
    max_requests_per_minute: int | None = None
    allowed_models: frozenset[str] | None = None


@dataclass(frozen=True)
class UpdateTenantPolicyResult:
    """Result DTO returned upon successful policy modification."""

    id: str
    tenant_id: str
    tier: str
    max_tokens_per_request: int
    monthly_budget_usd: Decimal
    max_requests_per_minute: int
    allowed_models: list[str]


class UpdateTenantPolicyCommandHandler:
    """Application use case for updating tenant operational governance policy."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initialize handler with transactional UnitOfWork boundary.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, command: UpdateTenantPolicyCommand) -> UpdateTenantPolicyResult:
        """Execute transactional update of tenant governance policy.

        Args:
            command: UpdateTenantPolicyCommand payload.

        Returns:
            UpdateTenantPolicyResult with updated policy parameters.

        Raises:
            TenantNotFoundError: If target tenant does not exist.
        """
        tenant_vo = TenantId(command.tenant_id)
        with self._unit_of_work as uow:
            tenant = uow.tenants.get_for_update(tenant_vo)
            if tenant is None:
                raise TenantNotFoundError(f"Tenant '{command.tenant_id}' no encontrado.")

            curr_policy = tenant.policy
            tier = TenantTier(command.tier) if command.tier else curr_policy.tier
            max_tokens = (
                command.max_tokens_per_request
                if command.max_tokens_per_request is not None
                else curr_policy.max_tokens_per_request
            )
            monthly_budget = (
                command.monthly_budget_usd
                if command.monthly_budget_usd is not None
                else curr_policy.monthly_budget_usd
            )
            max_requests = (
                command.max_requests_per_minute
                if command.max_requests_per_minute is not None
                else curr_policy.max_requests_per_minute
            )
            allowed_models = (
                command.allowed_models
                if command.allowed_models is not None
                else curr_policy.allowed_models
            )

            new_policy = TenantPolicy(
                tier=tier,
                max_tokens_per_request=max_tokens,
                monthly_budget_usd=monthly_budget,
                max_requests_per_minute=max_requests,
                allowed_models=allowed_models,
            )

            tenant.update_policy(new_policy)
            uow.tenants.add(tenant)
            uow.commit()

            return UpdateTenantPolicyResult(
                id=str(tenant.id),
                tenant_id=str(tenant.id),
                tier=new_policy.tier.value,
                max_tokens_per_request=new_policy.max_tokens_per_request,
                monthly_budget_usd=new_policy.monthly_budget_usd,
                max_requests_per_minute=new_policy.max_requests_per_minute,
                allowed_models=sorted(new_policy.allowed_models),
            )


__all__ = [
    "UpdateTenantPolicyCommand",
    "UpdateTenantPolicyCommandHandler",
    "UpdateTenantPolicyResult",
]
