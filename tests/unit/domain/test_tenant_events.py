"""Unit tests for Tenant domain events."""

from datetime import UTC, datetime
from decimal import Decimal

from src.domain.tenants.events.tenant_events import (
    ModelRouteFallbackActivatedDomainEvent,
    TenantBudgetReservedDomainEvent,
    TenantBudgetSettledDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)


def test_tenant_budget_reserved_event() -> None:
    now = datetime.now(UTC)
    event = TenantBudgetReservedDomainEvent(
        tenant_id="acme-corp",
        reserved_amount=Decimal("2.50"),
        remaining_balance=Decimal("47.50"),
        model_id="gpt-4o-mini",
        occurred_at=now,
    )
    assert event.tenant_id == "acme-corp"
    assert event.reserved_amount == Decimal("2.50")
    assert event.remaining_balance == Decimal("47.50")
    assert event.model_id == "gpt-4o-mini"
    assert event.occurred_at == now


def test_tenant_budget_settled_event() -> None:
    now = datetime.now(UTC)
    event = TenantBudgetSettledDomainEvent(
        tenant_id="acme-corp",
        actual_cost=Decimal("1.80"),
        new_balance=Decimal("48.20"),
        occurred_at=now,
    )
    assert event.tenant_id == "acme-corp"
    assert event.actual_cost == Decimal("1.80")
    assert event.new_balance == Decimal("48.20")
    assert event.occurred_at == now


def test_tenant_quota_exceeded_event() -> None:
    now = datetime.now(UTC)
    event = TenantQuotaExceededDomainEvent(
        tenant_id="acme-corp",
        requested_amount=Decimal("10.00"),
        available_balance=Decimal("1.20"),
        occurred_at=now,
    )
    assert event.tenant_id == "acme-corp"
    assert event.requested_amount == Decimal("10.00")
    assert event.available_balance == Decimal("1.20")
    assert event.occurred_at == now


def test_tenant_suspended_event() -> None:
    now = datetime.now(UTC)
    event = TenantSuspendedDomainEvent(
        tenant_id="acme-corp",
        reason="Account delinquent",
        occurred_at=now,
    )
    assert event.tenant_id == "acme-corp"
    assert event.reason == "Account delinquent"
    assert event.occurred_at == now


def test_model_route_fallback_activated_event() -> None:
    now = datetime.now(UTC)
    event = ModelRouteFallbackActivatedDomainEvent(
        tenant_id="acme-corp",
        primary_model_id="gpt-4o",
        fallback_model_id="gemini-1.5-pro",
        failure_reason="Upstream HTTP 503 Service Unavailable",
        occurred_at=now,
    )
    assert event.tenant_id == "acme-corp"
    assert event.primary_model_id == "gpt-4o"
    assert event.fallback_model_id == "gemini-1.5-pro"
    assert "HTTP 503" in event.failure_reason
    assert event.occurred_at == now
