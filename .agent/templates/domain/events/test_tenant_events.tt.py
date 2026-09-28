"""Test template canónico para Tenant Domain Events."""

from datetime import datetime, timezone
from decimal import Decimal
from .tenant_events import (
    ModelRouteFallbackActivatedDomainEvent,
    TenantBudgetReservedDomainEvent,
    TenantBudgetSettledDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)


def test_tenant_budget_reserved_event() -> None:
    now = datetime.now(timezone.utc)
    event = TenantBudgetReservedDomainEvent(
        tenant_id="tenant-123",
        reserved_amount=Decimal("2.50"),
        remaining_balance=Decimal("47.50"),
        model_id="gpt-4o-mini",
        occurred_at=now,
    )
    assert event.tenant_id == "tenant-123"
    assert event.reserved_amount == Decimal("2.50")
    assert event.model_id == "gpt-4o-mini"


def test_tenant_quota_exceeded_event() -> None:
    now = datetime.now(timezone.utc)
    event = TenantQuotaExceededDomainEvent(
        tenant_id="tenant-123",
        requested_amount=Decimal("10.00"),
        available_balance=Decimal("1.20"),
        occurred_at=now,
    )
    assert event.requested_amount == Decimal("10.00")
    assert event.available_balance == Decimal("1.20")


def test_fallback_activated_event() -> None:
    now = datetime.now(timezone.utc)
    event = ModelRouteFallbackActivatedDomainEvent(
        tenant_id="tenant-123",
        primary_model_id="gpt-4o",
        fallback_model_id="gemini-1.5-pro",
        failure_reason="Upstream HTTP 503 Service Unavailable",
        occurred_at=now,
    )
    assert event.primary_model_id == "gpt-4o"
    assert event.fallback_model_id == "gemini-1.5-pro"
