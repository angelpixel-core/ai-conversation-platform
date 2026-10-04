"""Tenant aggregate root for multi-tenant SaaS lifecycle and budget governance."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.events.tenant_events import (
    TenantBudgetReservedDomainEvent,
    TenantBudgetSettledDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)
from src.domain.tenants.exceptions import (
    InsufficientBudgetError,
    ModelNotAllowedError,
    TenantSuspendedError,
    TenantValidationError,
)
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


class TenantStatus(StrEnum):
    """Operational status of a tenant account."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class Tenant(AggregateRoot):
    """Aggregate Root representing a tenant organization in the platform.

    Encapsulates tenancy status, contractual policies, model permissions,
    and financial budget reservation / settlement workflows.
    """

    def __init__(
        self,
        tenant_id: TenantId,
        name: str,
        budget: MonetaryBudget,
        policy: TenantPolicy | None = None,
        status: TenantStatus = TenantStatus.ACTIVE,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Initialize a Tenant aggregate root.

        Args:
            tenant_id: Strongly-typed unique identifier of the tenant.
            name: Human-readable display name of the tenant organization.
            budget: Monetary budget value object tracking balances and reserves.
            policy: Optional usage and rate-limit policy. Defaults to FREE tier.
            status: Initial operational status. Defaults to ACTIVE.
            created_at: Optional UTC creation timestamp. Defaults to now.
            updated_at: Optional UTC modification timestamp. Defaults to now.

        Raises:
            TenantValidationError: If tenant name is empty or blank.
        """
        super().__init__()
        if not name.strip():
            raise TenantValidationError("El nombre del tenant no puede estar vacío.")

        self._id = tenant_id
        self._name = name.strip()
        self._budget = budget
        self._policy = policy or TenantPolicy()
        self._status = status
        now = datetime.now(UTC)
        self._created_at = created_at or now
        self._updated_at = updated_at or now

    @classmethod
    def create_demo(
        cls,
        tenant_id: TenantId | str = "corp-acme",
        name: str | None = None,
    ) -> "Tenant":
        """Factory initializing a pre-configured demo tenant for sandbox execution.

        Args:
            tenant_id: Target tenant identifier string or TenantId.
            name: Optional display name override.

        Returns:
            Fully initialized Tenant aggregate with pre-funded budget.
        """
        tid = TenantId(str(tenant_id))
        display_name = name or (
            "ACME Corporation" if str(tid) == "corp-acme" else "Default System Tenant"
        )
        return cls(
            tenant_id=tid,
            name=display_name,
            budget=MonetaryBudget(
                balance=Decimal("1000.00"),
                reserved_amount=Decimal("0.00"),
                currency="USD",
            ),
            policy=TenantPolicy(
                tier=TenantTier.STANDARD,
                max_tokens_per_request=4096,
                monthly_budget_usd=Decimal("500.00"),
                allowed_models=frozenset(
                    {
                        "gpt-4o",
                        "gpt-4o-mini",
                        "claude-3-5-sonnet",
                        "gemini-1.5-flash",
                    }
                ),
            ),
        )

    @property
    def id(self) -> TenantId:
        """TenantId: Unique aggregate identifier."""
        return self._id

    @property
    def name(self) -> str:
        """str: Organization or tenant name."""
        return self._name

    @property
    def budget(self) -> MonetaryBudget:
        """MonetaryBudget: Financial budget and reserve state."""
        return self._budget

    @property
    def policy(self) -> TenantPolicy:
        """TenantPolicy: Usage and model permissions policy."""
        return self._policy

    @property
    def status(self) -> TenantStatus:
        """TenantStatus: Current operational status."""
        return self._status

    @property
    def created_at(self) -> datetime:
        """datetime: UTC creation timestamp."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """datetime: UTC last updated timestamp."""
        return self._updated_at

    @property
    def is_active(self) -> bool:
        """bool: True if operational status is ACTIVE."""
        return self._status == TenantStatus.ACTIVE

    def can_operate(self) -> bool:
        """Determine if tenant has permission and positive available balance.

        Returns:
            True if tenant is ACTIVE and has available balance above 0.
        """
        return self.is_active and self._budget.available_balance > Decimal("0.00")

    def reserve_budget(self, estimated_cost: Decimal, model_id: str) -> None:
        """Attempt to reserve estimated budget for an inference request.

        Args:
            estimated_cost: Projected cost in USD for the completion.
            model_id: Target LLM model identifier.

        Raises:
            TenantSuspendedError: If tenant status is not ACTIVE.
            ModelNotAllowedError: If model_id is not allowed by policy.
            InsufficientBudgetError: If available balance is less than estimated cost.
        """
        if not self.is_active:
            raise TenantSuspendedError(f"El tenant '{self._id}' se encuentra suspendido.")

        if model_id not in self._policy.allowed_models:
            raise ModelNotAllowedError(
                f"El modelo '{model_id}' no está permitido para el tenant '{self._id}' "
                f"con plan {self._policy.tier.value}."
            )

        if not self._budget.can_reserve(estimated_cost):
            self.record_event(
                TenantQuotaExceededDomainEvent(
                    tenant_id=str(self._id),
                    requested_amount=estimated_cost,
                    available_balance=self._budget.available_balance,
                    occurred_at=datetime.now(UTC),
                )
            )
            raise InsufficientBudgetError(
                f"Cuota excedida para tenant '{self._id}'. Solicitado: {estimated_cost}, "
                f"Disponible: {self._budget.available_balance}"
            )

        self._budget = self._budget.reserve(estimated_cost)
        self._updated_at = datetime.now(UTC)

        self.record_event(
            TenantBudgetReservedDomainEvent(
                tenant_id=str(self._id),
                reserved_amount=estimated_cost,
                remaining_balance=self._budget.available_balance,
                model_id=model_id,
                occurred_at=self._updated_at,
            )
        )

    def settle_actual_cost(self, reserved_cost: Decimal, actual_cost: Decimal) -> None:
        """Settle actual consumed cost after streaming inference finishes.

        Args:
            reserved_cost: Previously reserved amount in USD.
            actual_cost: Actual metered cost calculated from token counts.
        """
        self._budget = self._budget.settle(reserved_cost=reserved_cost, actual_cost=actual_cost)
        self._updated_at = datetime.now(UTC)

        self.record_event(
            TenantBudgetSettledDomainEvent(
                tenant_id=str(self._id),
                actual_cost=actual_cost,
                new_balance=self._budget.balance,
                occurred_at=self._updated_at,
            )
        )

    def suspend(self, reason: str = "Administrative action") -> None:
        """Suspend tenant, blocking future inference operations.

        Args:
            reason: Human-readable justification for administrative suspension.
        """
        self._status = TenantStatus.SUSPENDED
        self._updated_at = datetime.now(UTC)
        self.record_event(
            TenantSuspendedDomainEvent(
                tenant_id=str(self._id),
                reason=reason,
                occurred_at=self._updated_at,
            )
        )

    def activate(self) -> None:
        """Re-activate a previously suspended tenant."""
        self._status = TenantStatus.ACTIVE
        self._updated_at = datetime.now(UTC)


__all__ = ["Tenant", "TenantStatus"]
