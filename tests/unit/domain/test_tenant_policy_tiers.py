"""Unit tests for TenantPolicy tiers, default SLAs, and policy update domain events."""

from datetime import UTC, datetime
from decimal import Decimal

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.events.tenant_events import TenantPolicyUpdatedDomainEvent
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_tenant_tier_enum_values() -> None:
    """Verify all four canonical tenant tiers exist as string enums."""
    assert TenantTier.FREE == "FREE"
    assert TenantTier.STANDARD == "STANDARD"
    assert TenantTier.PRO == "PRO"
    assert TenantTier.ENTERPRISE == "ENTERPRISE"
    assert len(TenantTier) == 4


def test_tenant_policy_defaults_for_all_tiers() -> None:
    """Verify default SLAs and token limits across all tiers."""
    free = TenantPolicy.default_for_tier(TenantTier.FREE)
    assert free.tier == TenantTier.FREE
    assert free.max_tokens_per_request == 2048
    assert free.monthly_budget_usd == Decimal("50.00")
    assert free.max_requests_per_minute == 30
    assert "gpt-4o-mini" in free.allowed_models

    standard = TenantPolicy.default_for_tier("STANDARD")
    assert standard.tier == TenantTier.STANDARD
    assert standard.max_tokens_per_request == 4096
    assert standard.monthly_budget_usd == Decimal("500.00")
    assert standard.max_requests_per_minute == 60
    assert "gpt-4o" in standard.allowed_models

    pro = TenantPolicy.default_for_tier(TenantTier.PRO)
    assert pro.tier == TenantTier.PRO
    assert pro.max_tokens_per_request == 8192
    assert pro.monthly_budget_usd == Decimal("2000.00")
    assert pro.max_requests_per_minute == 120
    assert "o1-mini" in pro.allowed_models

    enterprise = TenantPolicy.default_for_tier(TenantTier.ENTERPRISE)
    assert enterprise.tier == TenantTier.ENTERPRISE
    assert enterprise.max_tokens_per_request == 16384
    assert enterprise.monthly_budget_usd == Decimal("10000.00")
    assert enterprise.max_requests_per_minute == 300
    assert "claude-3-opus" in enterprise.allowed_models


def test_tenant_contact_email_initialization() -> None:
    """Verify tenant aggregate stores and trims contact_email."""
    tenant = Tenant(
        tenant_id=TenantId("corp-globex"),
        name="Globex Corp",
        budget=MonetaryBudget(balance=Decimal("100.00")),
        contact_email="  admin@globex.com  ",
    )
    assert tenant.contact_email == "admin@globex.com"

    tenant_no_email = Tenant(
        tenant_id=TenantId("corp-blank"),
        name="Blank Corp",
        budget=MonetaryBudget(balance=Decimal("100.00")),
    )
    assert tenant_no_email.contact_email is None


def test_tenant_update_policy_emits_domain_event() -> None:
    """Verify Tenant.update_policy updates policy, updated_at, and records domain event."""
    initial_time = datetime(2026, 1, 1, tzinfo=UTC)
    tenant = Tenant(
        tenant_id=TenantId("corp-acme"),
        name="Acme Corp",
        budget=MonetaryBudget(balance=Decimal("500.00")),
        policy=TenantPolicy.default_for_tier(TenantTier.FREE),
        created_at=initial_time,
        updated_at=initial_time,
    )
    assert tenant.policy.tier == TenantTier.FREE

    new_policy = TenantPolicy.default_for_tier(TenantTier.ENTERPRISE)
    tenant.update_policy(new_policy)

    assert tenant.policy.tier == TenantTier.ENTERPRISE
    assert tenant.policy.max_tokens_per_request == 16384
    assert tenant.updated_at > initial_time

    events = tenant.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, TenantPolicyUpdatedDomainEvent)
    assert event.tenant_id == "corp-acme"
    assert event.tier == "ENTERPRISE"
    assert event.max_tokens_per_request == 16384
    assert event.monthly_budget_usd == Decimal("10000.00")
