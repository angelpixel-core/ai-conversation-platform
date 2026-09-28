"""Unit tests for TenantDataMapper."""

from decimal import Decimal

from src.infrastructure.persistence.mssql.tenant_mapper import TenantDataMapper

from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import TenantModel, TenantPolicyModel


def test_mapper_to_model_and_back_roundtrip() -> None:
    original = Tenant(
        tenant_id=TenantId("corp-xyz"),
        name="XYZ Corp",
        budget=MonetaryBudget(
            balance=Decimal("200.5000"),
            currency="USD",
            reserved_amount=Decimal("15.2500"),
        ),
        policy=TenantPolicy(
            tier=TenantTier.ENTERPRISE,
            max_tokens_per_request=16384,
            monthly_budget_usd=Decimal("1000.0000"),
            allowed_models=frozenset({"gpt-4o", "gemini-1.5-pro"}),
        ),
        status=TenantStatus.ACTIVE,
    )

    model = TenantDataMapper.to_model(original)
    assert model.id == "corp-xyz"
    assert model.name == "XYZ Corp"
    assert model.balance_usd == Decimal("200.5000")
    assert model.reserved_usd == Decimal("15.2500")
    assert model.currency == "USD"
    assert model.status == "ACTIVE"
    assert model.policy is not None
    assert model.policy.tenant_id == "corp-xyz"
    assert model.policy.tier == "ENTERPRISE"
    assert model.policy.max_tokens_per_request == 16384
    assert model.policy.monthly_budget_usd == Decimal("1000.0000")

    reconstituted = TenantDataMapper.to_domain(model)
    assert reconstituted.id == original.id
    assert reconstituted.name == original.name
    assert reconstituted.budget.balance == original.budget.balance
    assert reconstituted.budget.reserved_amount == original.budget.reserved_amount
    assert reconstituted.budget.currency == original.budget.currency
    assert reconstituted.policy.tier == TenantTier.ENTERPRISE
    assert reconstituted.policy.max_tokens_per_request == 16384
    assert reconstituted.policy.monthly_budget_usd == Decimal("1000.0000")
    assert reconstituted.policy.allowed_models == frozenset({"gpt-4o", "gemini-1.5-pro"})
    assert reconstituted.status == TenantStatus.ACTIVE


def test_mapper_to_domain_with_none_policy() -> None:
    model = TenantModel(
        id="orphan-tenant",
        name="Orphan Tenant",
        balance_usd=Decimal("50.0000"),
        reserved_usd=Decimal("0.0000"),
        currency="USD",
        status="ACTIVE",
        policy=None,
    )

    domain = TenantDataMapper.to_domain(model)
    assert domain.id.value == "orphan-tenant"
    assert domain.policy.tier == TenantTier.FREE
    assert domain.policy.max_tokens_per_request == 4096
    assert domain.policy.monthly_budget_usd == Decimal("50.00")
    assert "gpt-4o-mini" in domain.policy.allowed_models


def test_mapper_to_domain_suspended_status() -> None:
    model = TenantModel(
        id="suspended-corp",
        name="Suspended Corp",
        balance_usd=Decimal("0.0000"),
        reserved_usd=Decimal("0.0000"),
        currency="USD",
        status="SUSPENDED",
        policy=TenantPolicyModel(
            tenant_id="suspended-corp",
            tier="FREE",
            max_tokens_per_request=2048,
            monthly_budget_usd=Decimal("10.0000"),
            allowed_models_json='["gpt-4o-mini"]',
        ),
    )

    domain = TenantDataMapper.to_domain(model)
    assert domain.status == TenantStatus.SUSPENDED
    assert not domain.is_active
