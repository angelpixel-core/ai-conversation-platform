"""Unit tests for TenantMapper."""

from decimal import Decimal

from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import TenantModel, TenantPolicyModel
from src.infrastructure.persistence.mssql.tenant_mapper import TenantMapper


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

    model = TenantMapper.to_model(original)
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

    reconstituted = TenantMapper.to_domain(model)
    assert reconstituted.id == original.id
    assert reconstituted.name == original.name
    assert reconstituted.budget.balance == original.budget.balance
    assert reconstituted.budget.reserved_amount == original.budget.reserved_amount
    assert reconstituted.budget.currency == original.budget.currency
    assert reconstituted.policy.tier == TenantTier.ENTERPRISE
    assert reconstituted.policy.max_tokens_per_request == 16384
    assert reconstituted.policy.monthly_budget_usd == Decimal("1000.0000")
    assert reconstituted.policy.max_requests_per_minute == 60
    assert reconstituted.policy.allowed_models == frozenset({"gpt-4o", "gemini-1.5-pro"})
    assert reconstituted.status == TenantStatus.ACTIVE
    assert reconstituted.contact_email is None


def test_mapper_pro_tier_and_metadata_roundtrip() -> None:
    original = Tenant(
        tenant_id=TenantId("pro-tenant-42"),
        name="Pro Scale Corp",
        budget=MonetaryBudget(
            balance=Decimal("500.0000"),
            currency="USD",
            reserved_amount=Decimal("0.0000"),
        ),
        policy=TenantPolicy(
            tier=TenantTier.PRO,
            max_tokens_per_request=8192,
            monthly_budget_usd=Decimal("250.0000"),
            max_requests_per_minute=120,
            allowed_models=frozenset({"gpt-4o", "claude-3-5-sonnet"}),
        ),
        contact_email="devops@proscale.io",
        status=TenantStatus.ACTIVE,
    )

    model = TenantMapper.to_model(original)
    assert model.id == "pro-tenant-42"
    assert model.contact_email == "devops@proscale.io"
    assert model.policy is not None
    assert model.policy.tier == "PRO"
    assert model.policy.max_requests_per_minute == 120
    assert model.policy.max_tokens_per_request == 8192

    reconstituted = TenantMapper.to_domain(model)
    assert reconstituted.id.value == "pro-tenant-42"
    assert reconstituted.contact_email == "devops@proscale.io"
    assert reconstituted.policy.tier == TenantTier.PRO
    assert reconstituted.policy.max_requests_per_minute == 120
    assert reconstituted.policy.max_tokens_per_request == 8192
    assert reconstituted.policy.allowed_models == frozenset({"gpt-4o", "claude-3-5-sonnet"})


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

    domain = TenantMapper.to_domain(model)
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

    domain = TenantMapper.to_domain(model)
    assert domain.status == TenantStatus.SUSPENDED
    assert not domain.is_active
