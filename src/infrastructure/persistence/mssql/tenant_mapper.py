"""Data mapper between Tenant domain aggregate root and MSSQL physical models."""

import json
from decimal import Decimal

from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import TenantModel, TenantPolicyModel


class TenantDataMapper:
    """Bidirectional data mapper between domain entities and SQLModel database models."""

    @staticmethod
    def to_domain(model: TenantModel) -> Tenant:
        """Reconstitute the Tenant aggregate from the relational database models."""
        policy_model = model.policy
        allowed_models: set[str] = (
            set(json.loads(policy_model.allowed_models_json))
            if policy_model and policy_model.allowed_models_json
            else {"gpt-4o-mini"}
        )

        policy = TenantPolicy(
            tier=TenantTier(policy_model.tier) if policy_model else TenantTier.FREE,
            max_tokens_per_request=policy_model.max_tokens_per_request if policy_model else 4096,
            monthly_budget_usd=policy_model.monthly_budget_usd
            if policy_model
            else Decimal("50.00"),
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
        """Map Tenant aggregate root to SQLModel physical database records."""
        policy_model = TenantPolicyModel(
            tenant_id=entity.id.value,
            tier=entity.policy.tier.value,
            max_tokens_per_request=entity.policy.max_tokens_per_request,
            monthly_budget_usd=entity.policy.monthly_budget_usd,
            allowed_models_json=json.dumps(sorted(entity.policy.allowed_models)),
        )

        model = TenantModel(
            id=entity.id.value,
            name=entity.name,
            status=entity.status.value,
            balance_usd=entity.budget.balance,
            reserved_usd=entity.budget.reserved_amount,
            currency=entity.budget.currency,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            policy=policy_model,
        )
        return model
