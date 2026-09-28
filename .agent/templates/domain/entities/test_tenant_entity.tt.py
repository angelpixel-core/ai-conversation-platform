"""Test template canónico para Tenant Aggregate Root."""

from decimal import Decimal
import pytest
from ..value_objects.tenant_id import TenantId
from ..value_objects.monetary_budget import MonetaryBudget
from ..events.tenant_events import (
    TenantBudgetReservedDomainEvent,
    TenantQuotaExceededDomainEvent,
    TenantSuspendedDomainEvent,
)
from .tenant_entity import Tenant, TenantPolicy, TenantStatus, TenantTier


def test_tenant_creation_valid() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme Corporation", budget=budget)

    assert tenant.id == tid
    assert tenant.name == "Acme Corporation"
    assert tenant.is_active is True
    assert tenant.budget.available_balance == Decimal("50.00")


def test_tenant_reserve_budget_success_emits_event() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget)

    tenant.reserve_budget(estimated_cost=Decimal("5.00"), model_id="gpt-4o-mini")

    assert tenant.budget.available_balance == Decimal("45.00")
    events = tenant.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], TenantBudgetReservedDomainEvent)
    assert events[0].reserved_amount == Decimal("5.00")
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
    assert events[0].requested_amount == Decimal("15.00")


def test_tenant_reserve_disallowed_model_raises_error() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    policy = TenantPolicy(tier=TenantTier.FREE, allowed_models=frozenset({"gpt-4o-mini"}))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget, policy=policy)

    with pytest.raises(ValueError, match="no está permitido"):
        tenant.reserve_budget(estimated_cost=Decimal("1.00"), model_id="o1-preview")


def test_tenant_suspended_cannot_reserve() -> None:
    tid = TenantId("acme-corp")
    budget = MonetaryBudget(balance=Decimal("50.00"))
    tenant = Tenant(tenant_id=tid, name="Acme", budget=budget)

    tenant.suspend(reason="Non-payment")
    assert tenant.is_active is False

    events = tenant.pull_events()
    assert any(isinstance(e, TenantSuspendedDomainEvent) for e in events)

    with pytest.raises(ValueError, match="se encuentra suspendido"):
        tenant.reserve_budget(estimated_cost=Decimal("1.00"), model_id="gpt-4o-mini")
