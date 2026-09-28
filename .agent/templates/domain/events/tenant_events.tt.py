"""Template canónico para Domain Events de Tenancy, Budgets y Routing.

Reglas:
- Inmutables por diseño (@dataclass(frozen=True)).
- Transportan datos primitivos o nativos para serialización sin acoplamiento.
- Indican un hecho ya acaecido en el pasado.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class TenantBudgetReservedDomainEvent:
    """Evento emitido cuando se reserva saldo con éxito para una inferencia."""

    tenant_id: str
    reserved_amount: Decimal
    remaining_balance: Decimal
    model_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class TenantBudgetSettledDomainEvent:
    """Evento emitido al liquidar el costo final real de una inferencia."""

    tenant_id: str
    actual_cost: Decimal
    new_balance: Decimal
    occurred_at: datetime


@dataclass(frozen=True)
class TenantQuotaExceededDomainEvent:
    """Evento emitido cuando un tenant intenta consumir por encima de su saldo disponible."""

    tenant_id: str
    requested_amount: Decimal
    available_balance: Decimal
    occurred_at: datetime


@dataclass(frozen=True)
class TenantSuspendedDomainEvent:
    """Evento emitido cuando un tenant cambia a estado suspendido."""

    tenant_id: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True)
class ModelRouteFallbackActivatedDomainEvent:
    """Evento emitido cuando el proveedor primario falla y se activa el fallback."""

    tenant_id: str
    primary_model_id: str
    fallback_model_id: str
    failure_reason: str
    occurred_at: datetime
