"""Unit tests for ProvisionTenantCommand and ProvisionTenantCommandHandler."""

from decimal import Decimal

import pytest

from src.application.tenants.commands.provision_tenant_command import (
    ProvisionTenantCommand,
    ProvisionTenantCommandHandler,
)
from src.domain.tenants.entities.tenant_policy import TenantTier
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_provision_tenant_success() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    handler = ProvisionTenantCommandHandler(unit_of_work=uow)

    command = ProvisionTenantCommand(
        tenant_id="tenant-beta",
        name="Beta Organization",
        initial_balance=Decimal("250.00"),
        tier="ENTERPRISE",
        max_tokens_per_request=8192,
        monthly_budget_usd=Decimal("1500.00"),
        allowed_models=frozenset({"gpt-4o", "claude-3-5-sonnet"}),
    )

    result = handler.handle(command)

    assert result.tenant_id == "tenant-beta"
    assert result.name == "Beta Organization"
    assert result.balance == Decimal("250.00")
    assert result.reserved_amount == Decimal("0.00")
    assert result.available_balance == Decimal("250.00")
    assert result.currency == "USD"

    # Verify retrieval
    with uow:
        retrieved = uow.tenants.get(command.tenant_id)  # type: ignore[arg-type]
        assert retrieved is not None
        assert retrieved.policy.tier == TenantTier.ENTERPRISE
        assert retrieved.policy.max_tokens_per_request == 8192


def test_provision_tenant_duplicate_fails() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    handler = ProvisionTenantCommandHandler(unit_of_work=uow)

    command = ProvisionTenantCommand(
        tenant_id="tenant-alpha",
        name="Alpha Org",
    )
    handler.handle(command)

    with pytest.raises(ValueError, match="ya existe"):
        handler.handle(command)
