"""Unit tests for Tenant aggregate root and TenantPolicy entity."""

from decimal import Decimal

import pytest
from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.events.tenant_events import (
    TenantBudgetReservedDomainEvent,
    TenantBudgetSettledDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)

from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_tenant_creation_valid() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme Corporation", budget=budget)

    assert tenant.id == tid
    assert tenant.name == "Acme Corporation"
    assert tenant.is_active is True
    assert tenant.can_operate() is True
    assert tenant.budget.available_balance == Decimal("50.00")
    assert tenant.policy.tier == TenantTier.FREE


def test_tenant_empty_name_raises_error() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    with pytest.raises(ValueError, match="nombre del tenant no puede estar vacío"):
        Tenant(tenant_id=tid, name="   ", budget=budget)


def test_tenant_reserve_budget_success_emits_event() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget)

    tenant.reserve_budget(estimated_cost=Decimal("5.00"), model_id="gpt-4o-mini")

    assert tenant.budget.available_balance == Decimal("45.00")
    events = tenant.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], TenantBudgetReservedDomainEvent)
    assert events[0].tenant_id == "acme-corp"
    assert events[0].reserved_amount == Decimal("5.00")
    assert events[0].remaining_balance == Decimal("45.00")
    assert events[0].model_id == "gpt-4o-mini"


def test_tenant_reserve_budget_exceeded_emits_quota_exceeded_event() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("10.00"))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget)

    with pytest.raises(ValueError, match="Cuota excedida"):
        tenant.reserve_budget(estimated_cost=Decimal("15.00"), model_id="gpt-4o-mini")

    events = tenant.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], TenantQuotaExceededDomainEvent)
    assert events[0].tenant_id == "acme-corp"
    assert events[0].requested_amount == Decimal("15.00")
    assert events[0].available_balance == Decimal("10.00")


def test_tenant_reserve_disallowed_model_raises_error() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    policy = TenantPolicy(tier=TenantTier.FREE, allowed_models=frozenset({"gpt-4o-mini"}))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget, policy=policy)

    with pytest.raises(ValueError, match="no está permitido"):
        tenant.reserve_budget(estimated_cost=Decimal("1.00"), model_id="o1-preview")


def test_tenant_settle_actual_cost_emits_settled_event() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget)

    tenant.reserve_budget(estimated_cost=Decimal("5.00"), model_id="gpt-4o-mini")
    _ = tenant.pull_events()  # Clear reserve event

    tenant.settle_actual_cost(reserved_cost=Decimal("5.00"), actual_cost=Decimal("3.50"))

    assert tenant.budget.balance == Decimal("46.50")
    assert tenant.budget.available_balance == Decimal("46.50")

    events = tenant.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], TenantBudgetSettledDomainEvent)
    assert events[0].actual_cost == Decimal("3.50")
    assert events[0].new_balance == Decimal("46.50")


def test_tenant_suspend_and_activate() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget)

    tenant.suspend(reason="Payment overdue")
    assert tenant.is_active is False
    assert tenant.status == TenantStatus.SUSPENDED
    assert tenant.can_operate() is False

    events = tenant.pull_events()
    assert any(isinstance(e, TenantSuspendedDomainEvent) for e in events)

    with pytest.raises(ValueError, match="se encuentra suspendido"):
        tenant.reserve_budget(estimated_cost=Decimal("1.00"), model_id="gpt-4o-mini")

    tenant.activate()
    assert tenant.is_active is True
    assert tenant.status == TenantStatus.ACTIVE
    assert tenant.can_operate() is True
