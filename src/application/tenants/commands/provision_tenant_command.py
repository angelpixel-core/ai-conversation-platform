"""Provision tenant command and handler for registering new tenants."""

from dataclasses import dataclass
from decimal import Decimal

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.exceptions import TenantAlreadyExistsError
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class ProvisionTenantCommand:
    """Command DTO to provision a new tenant."""

    tenant_id: str
    name: str
    initial_balance: Decimal = Decimal("1000.00")
    tier: str = "STANDARD"
    max_tokens_per_request: int = 4096
    monthly_budget_usd: Decimal = Decimal("500.00")
    allowed_models: frozenset[str] = frozenset(
        {"gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-flash"}
    )


@dataclass(frozen=True)
class ProvisionTenantResult:
    """Result DTO returned upon tenant provisioning."""

    tenant_id: str
    name: str
    balance: Decimal
    reserved_amount: Decimal
    available_balance: Decimal
    currency: str


class ProvisionTenantCommandHandler:
    """Application use case for registering and provisioning new tenants."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initializes the handler with a transactional unit of work.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, command: ProvisionTenantCommand) -> ProvisionTenantResult:
        """Provisions a new tenant with initial budget and policy configuration.

        Args:
            command: ProvisionTenantCommand payload.

        Returns:
            ProvisionTenantResult with tenant metadata and initial balance.

        Raises:
            TenantAlreadyExistsError: If tenant identifier is already registered.
        """
        tenant_vo = TenantId(command.tenant_id)
        with self._unit_of_work as uow:
            existing = uow.tenants.get(tenant_vo)
            if existing is not None:
                raise TenantAlreadyExistsError(f"Tenant '{command.tenant_id}' ya existe.")

            try:
                tier_enum = TenantTier(command.tier)
            except ValueError:
                tier_enum = TenantTier.STANDARD

            policy = TenantPolicy(
                tier=tier_enum,
                max_tokens_per_request=command.max_tokens_per_request,
                monthly_budget_usd=command.monthly_budget_usd,
                allowed_models=command.allowed_models,
            )
            tenant = Tenant(
                tenant_id=tenant_vo,
                name=command.name,
                budget=MonetaryBudget(
                    balance=command.initial_balance,
                    reserved_amount=Decimal("0.00"),
                    currency="USD",
                ),
                policy=policy,
            )
            uow.tenants.add(tenant)
            uow.commit()

            return ProvisionTenantResult(
                tenant_id=str(tenant.id),
                name=tenant.name,
                balance=tenant.budget.balance,
                reserved_amount=tenant.budget.reserved_amount,
                available_balance=tenant.budget.available_balance,
                currency=tenant.budget.currency,
            )


# Alias for backward compatibility
ProvisionTenantHandler = ProvisionTenantCommandHandler
