"""Template canónico para TenantMapper en Clean Architecture.

Reglas:
- Pertenece a src/infrastructure/persistence/mssql/tenant_mapper.py.
- Transforma bidireccionalmente entre el agregado puro Tenant y los modelos relacionales TenantModel.
- Maneja serialización/deserialización JSON de allowed_models.
"""

from decimal import Decimal
import json
from typing import Set

from src.domain.tenants.entities.tenant_entity import (
    Tenant,
    TenantPolicy,
    TenantStatus,
    TenantTier,
)
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from .tenant_model import TenantModel, TenantPolicyModel


class TenantDataMapper:
    """Mapeador de datos entre la entidad Tenant y los modelos relacionales SQLModel."""

    @staticmethod
    def to_domain(model: TenantModel) -> Tenant:
        """Reconstituye el agregado Tenant a partir de los modelos de base de datos."""
        policy_model = model.policy
        allowed_models: Set[str] = (
            set(json.loads(policy_model.allowed_models_json))
            if policy_model and policy_model.allowed_models_json
            else {"gpt-4o-mini"}
        )

        policy = TenantPolicy(
            tier=TenantTier(policy_model.tier) if policy_model else TenantTier.FREE,
            max_tokens_per_request=policy_model.max_tokens_per_request if policy_model else 4096,
            monthly_budget_usd=policy_model.monthly_budget_usd if policy_model else Decimal("50.00"),
            allowed_models=frozenset(allowed_models),
        )

        budget = MonetaryBudget(
            balance=model.balance_usd,
            currency=model.currency,
            reserved_amount=model.reserved_usd,
        )

        return Tenant(
            tenant_id=TenantId(model.id),
            name=model.name,
            budget=budget,
            policy=policy,
            status=TenantStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Tenant) -> TenantModel:
        """Convierte una entidad Tenant al modelo físico TenantModel."""
        policy_model = TenantPolicyModel(
            tenant_id=str(entity.id),
            tier=entity.policy.tier.value,
            max_tokens_per_request=entity.policy.max_tokens_per_request,
            monthly_budget_usd=entity.policy.monthly_budget_usd,
            allowed_models_json=json.dumps(list(entity.policy.allowed_models)),
        )

        model = TenantModel(
            id=str(entity.id),
            name=entity.name,
            status=entity.status.value,
            balance_usd=entity.budget.balance,
            reserved_usd=entity.budget.reserved_amount,
            currency=entity.budget.currency,
            created_at=entity._created_at,  # type: ignore[attr-defined]
            updated_at=entity._updated_at,  # type: ignore[attr-defined]
            policy=policy_model,
        )
        return model
