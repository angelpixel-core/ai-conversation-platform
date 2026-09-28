"""Test template canónico para TenantDataMapper."""

from decimal import Decimal
from src.domain.tenants.entities.tenant_entity import Tenant, TenantPolicy, TenantStatus, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from .tenant_mapper import TenantDataMapper
from .tenant_model import TenantModel, TenantPolicyModel


def test_mapper_to_model_and_back() -> None:
    original = Tenant(
        tenant_id=TenantId("corp-xyz"),
        name="XYZ Corp",
        budget=MonetaryBudget(balance=Decimal("200.00"), reserved_amount=Decimal("15.00")),
        policy=TenantPolicy(
            tier=TenantTier.ENTERPRISE,
            max_tokens_per_request=16384,
            monthly_budget_usd=Decimal("1000.00"),
            allowed_models=frozenset({"gpt-4o", "gemini-1.5-pro"}),
        ),
        status=TenantStatus.ACTIVE,
    )

    model = TenantDataMapper.to_model(original)
    assert model.id == "corp-xyz"
    assert model.name == "XYZ Corp"
    assert model.balance_usd == Decimal("200.00")
    assert model.reserved_usd == Decimal("15.00")
    assert model.policy is not None
    assert model.policy.tier == "ENTERPRISE"

    reconstituted = TenantDataMapper.to_domain(model)
    assert reconstituted.id == original.id
    assert reconstituted.name == original.name
    assert reconstituted.budget.balance == original.budget.balance
    assert reconstituted.budget.reserved_amount == original.budget.reserved_amount
    assert reconstituted.policy.tier == TenantTier.ENTERPRISE
    assert "gpt-4o" in reconstituted.policy.allowed_models
