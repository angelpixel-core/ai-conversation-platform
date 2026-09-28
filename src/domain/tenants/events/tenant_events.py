"""Domain events for tenant management, budgeting, and routing."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class TenantBudgetReservedDomainEvent:
    """Emitted when budget is successfully reserved for an inference request."""

    tenant_id: str
    reserved_amount: Decimal
    remaining_balance: Decimal
    model_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class TenantBudgetSettledDomainEvent:
    """Emitted when actual token cost is settled following inference stream completion."""

    tenant_id: str
    actual_cost: Decimal
    new_balance: Decimal
    occurred_at: datetime


@dataclass(frozen=True)
class TenantQuotaExceededDomainEvent:
    """Emitted when a tenant attempts to exceed available budget or quota."""

    tenant_id: str
    requested_amount: Decimal
    available_balance: Decimal
    occurred_at: datetime


@dataclass(frozen=True)
class TenantSuspendedDomainEvent:
    """Emitted when a tenant is suspended."""

    tenant_id: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True)
class ModelRouteFallbackActivatedDomainEvent:
    """Emitted when a primary model route fails and a fallback route is triggered."""

    tenant_id: str
    primary_model_id: str
    fallback_model_id: str
    failure_reason: str
    occurred_at: datetime
