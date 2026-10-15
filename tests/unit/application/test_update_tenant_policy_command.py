"""Unit tests for UpdateTenantPolicyCommand and UpdateTenantPolicyCommandHandler."""

from decimal import Decimal

import pytest

from src.application.tenants.commands.update_tenant_policy_command import (
    UpdateTenantPolicyCommand,
    UpdateTenantPolicyCommandHandler,
)
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.events.tenant_events import TenantPolicyUpdatedDomainEvent
from src.domain.tenants.exceptions import TenantNotFoundError
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_update_tenant_policy_success() -> None:
    """Verify updating policy mutates aggregate, emits domain event, and returns result."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = UpdateTenantPolicyCommandHandler(unit_of_work=uow)

    tenant = Tenant(
        tenant_id=TenantId("corp-update"),
        name="Update Corp",
        budget=MonetaryBudget(balance=Decimal("100.00")),
        policy=TenantPolicy.default_for_tier(TenantTier.FREE),
    )
    with uow:
        uow.tenants.add(tenant)
        uow.commit()

    command = UpdateTenantPolicyCommand(
        tenant_id="corp-update",
        tier="PRO",
        max_tokens_per_request=8192,
        monthly_budget_usd=Decimal("2500.00"),
        max_requests_per_minute=150,
        allowed_models=frozenset({"gpt-4o", "claude-3-5-sonnet", "o1-mini"}),
    )

    result = handler.handle(command)

    assert result.id == "corp-update"
    assert result.tenant_id == "corp-update"
    assert result.tier == "PRO"
    assert result.max_tokens_per_request == 8192
    assert result.monthly_budget_usd == Decimal("2500.00")
    assert result.max_requests_per_minute == 150
    assert result.allowed_models == ["claude-3-5-sonnet", "gpt-4o", "o1-mini"]

    # Verify persisted state and domain event in repository
    with uow:
        saved = uow.tenants.get(TenantId("corp-update"))
        assert saved is not None
        assert saved.policy.tier == TenantTier.PRO
        assert saved.policy.max_tokens_per_request == 8192
        assert saved.policy.max_requests_per_minute == 150
        events = saved.pull_events()
        assert any(isinstance(e, TenantPolicyUpdatedDomainEvent) for e in events)


def test_update_tenant_policy_not_found_raises() -> None:
    """Verify updating non-existent tenant raises TenantNotFoundError."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = UpdateTenantPolicyCommandHandler(unit_of_work=uow)

    command = UpdateTenantPolicyCommand(
        tenant_id="missing-corp",
        tier="STANDARD",
    )
    with pytest.raises(TenantNotFoundError, match="no encontrado"):
        handler.handle(command)
