"""Tenant aggregate root for multi-tenant SaaS lifecycle and budget governance."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.entities.tenant_policy import TenantPolicy
from src.domain.tenants.events.tenant_events import (
    TenantBudgetReservedDomainEvent,
    TenantBudgetSettledDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


class TenantStatus(StrEnum):
    """Operational status of a tenant account."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class Tenant(AggregateRoot):
    """Aggregate Root representing a tenant organization in the platform."""

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
        super().__init__()
        if not name.strip():
            raise ValueError("El nombre del tenant no puede estar vacío.")

        self._id = tenant_id
        self._name = name.strip()
        self._budget = budget
        self._policy = policy or TenantPolicy()
        self._status = status
        now = datetime.now(UTC)
        self._created_at = created_at or now
        self._updated_at = updated_at or now

    @property
    def id(self) -> TenantId:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def budget(self) -> MonetaryBudget:
        return self._budget

    @property
    def policy(self) -> TenantPolicy:
        return self._policy

    @property
    def status(self) -> TenantStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def is_active(self) -> bool:
        return self._status == TenantStatus.ACTIVE

    def can_operate(self) -> bool:
        """Determines if the tenant has permission and positive balance to run inferences."""
        return self.is_active and self._budget.available_balance > Decimal("0.00")

    def reserve_budget(self, estimated_cost: Decimal, model_id: str) -> None:
        """Attempts to reserve estimated budget for an inference request."""
        if not self.is_active:
            raise ValueError(f"El tenant '{self._id}' se encuentra suspendido.")

        if model_id not in self._policy.allowed_models:
            raise ValueError(
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
            raise ValueError(
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
        """Settles actual consumed cost after streaming inference finishes."""
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
        """Suspends tenant, blocking future inference operations."""
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
        """Re-activates a suspended tenant."""
        self._status = TenantStatus.ACTIVE
        self._updated_at = datetime.now(UTC)
