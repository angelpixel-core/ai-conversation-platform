"""Test template canónico para TenantModel y TenantPolicyModel (SQLModel)."""

from decimal import Decimal
from .tenant_model import TenantModel, TenantPolicyModel


def test_tenant_model_instantiation() -> None:
    tenant = TenantModel(
        id="acme-saas",
        name="Acme SaaS",
        balance_usd=Decimal("150.50"),
        reserved_usd=Decimal("20.00"),
        currency="USD",
    )
    assert tenant.id == "acme-saas"
    assert tenant.name == "Acme SaaS"
    assert tenant.balance_usd == Decimal("150.50")
    assert tenant.reserved_usd == Decimal("20.00")
    assert tenant.status == "ACTIVE"


def test_tenant_policy_model_instantiation() -> None:
    policy = TenantPolicyModel(
        tenant_id="acme-saas",
        tier="ENTERPRISE",
        max_tokens_per_request=8192,
        monthly_budget_usd=Decimal("500.00"),
        allowed_models_json='["gpt-4o", "gemini-1.5-pro"]',
    )
    assert policy.tenant_id == "acme-saas"
    assert policy.tier == "ENTERPRISE"
    assert policy.max_tokens_per_request == 8192
