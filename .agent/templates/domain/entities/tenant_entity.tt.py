"""Template canónico para la Entidad Aggregate Root Tenant (DDD).

Reglas:
- Extiende de AggregateRoot para grabar y emitir Domain Events.
- Encapsula invariantes de negocio: control de saldo, políticas de cuota y suspensión.
- 100% puro en Python (sin dependencias a frameworks externos).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Set

from src.domain.shared.aggregate_root import AggregateRoot
from ..value_objects.tenant_id import TenantId
from ..value_objects.monetary_budget import MonetaryBudget
from ..events.tenant_events import (
    TenantBudgetReservedDomainEvent,
    TenantBudgetSettledDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)


class TenantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class TenantTier(str, Enum):
    FREE = "FREE"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"


@dataclass(frozen=True)
class TenantPolicy:
    """Política contractual de consumo y modelos para un inquilino."""

    tier: TenantTier = TenantTier.FREE
    max_tokens_per_request: int = 4096
    monthly_budget_usd: Decimal = Decimal("50.00")
    allowed_models: Set[str] = frozenset({"gpt-4o-mini", "gemini-1.5-flash"})  # type: ignore[assignment]


class Tenant(AggregateRoot):
    """Aggregate Root que representa una organización inquilina en el SaaS."""

    def __init__(
        self,
        tenant_id: TenantId,
        name: str,
        budget: MonetaryBudget,
        policy: Optional[TenantPolicy] = None,
        status: TenantStatus = TenantStatus.ACTIVE,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__()
        if not name.strip():
            raise ValueError("El nombre del tenant no puede estar vacío.")

        self._id = tenant_id
        self._name = name.strip()
        self._budget = budget
        self._policy = policy or TenantPolicy()
        self._status = status
        now = datetime.now(timezone.utc)
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
    def is_active(self) -> bool:
        return self._status == TenantStatus.ACTIVE

    def can_operate(self) -> bool:
        """Determina si el inquilino tiene permiso para ejecutar inferencias."""
        return self.is_active and self._budget.available_balance > Decimal("0.00")

    def reserve_budget(self, estimated_cost: Decimal, model_id: str) -> None:
        """Intenta reservar presupuesto para una solicitud de inferencia."""
        if not self.is_active:
            raise ValueError(f"El tenant '{self._id}' se encuentra suspendido.")

        if model_id not in self._policy.allowed_models:
            raise ValueError(
                f"El modelo '{model_id}' no está permitido para el tenant '{self._id}' con plan {self._policy.tier.value}."
            )

        if not self._budget.can_reserve(estimated_cost):
            self.record_event(
                TenantQuotaExceededDomainEvent(
                    tenant_id=str(self._id),
                    requested_amount=estimated_cost,
                    available_balance=self._budget.available_balance,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            raise ValueError(
                f"Cuota excedida para tenant '{self._id}'. Solicitado: {estimated_cost}, Disponible: {self._budget.available_balance}"
            )

        self._budget = self._budget.reserve(estimated_cost)
        self._updated_at = datetime.now(timezone.utc)

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
        """Liquida el costo real consumido tras completar el stream de inferencia."""
        self._budget = self._budget.settle(reserved_cost=reserved_cost, actual_cost=actual_cost)
        self._updated_at = datetime.now(timezone.utc)

        self.record_event(
            TenantBudgetSettledDomainEvent(
                tenant_id=str(self._id),
                actual_cost=actual_cost,
                new_balance=self._budget.balance,
                occurred_at=self._updated_at,
            )
        )

    def suspend(self, reason: str = "Administrative action") -> None:
        """Suspende al inquilino impidiendo nuevas inferencias."""
        self._status = TenantStatus.SUSPENDED
        self._updated_at = datetime.now(timezone.utc)
        self.record_event(
            TenantSuspendedDomainEvent(
                tenant_id=str(self._id),
                reason=reason,
                occurred_at=self._updated_at,
            )
        )

    def activate(self) -> None:
        """Reactiva al inquilino suspendido."""
        self._status = TenantStatus.ACTIVE
        self._updated_at = datetime.now(timezone.utc)
