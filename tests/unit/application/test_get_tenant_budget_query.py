"""Unit tests for GetTenantBudgetQuery and GetTenantBudgetQueryHandler."""

from decimal import Decimal

import pytest

from src.application.tenants.queries.get_tenant_budget_query import (
    GetTenantBudgetQuery,
    GetTenantBudgetQueryHandler,
)
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.exceptions import TenantNotFoundError
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_get_tenant_budget_success() -> None:
    """Verify handler returns accurate budget figures and dual identifiers."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = GetTenantBudgetQueryHandler(unit_of_work=uow)

    tenant = Tenant(
        tenant_id=TenantId("corp-acme"),
        name="ACME Corporation",
        budget=MonetaryBudget(
            balance=Decimal("500.00"),
            reserved_amount=Decimal("50.00"),
            currency="USD",
        ),
    )
    with uow:
        uow.tenants.add(tenant)
        uow.commit()

    result = handler.handle(GetTenantBudgetQuery(tenant_id="corp-acme"))

    assert result.id == "corp-acme"
    assert result.tenant_id == "corp-acme"
    assert result.balance == Decimal("500.00")
    assert result.reserved_amount == Decimal("50.00")
    assert result.available_balance == Decimal("450.00")
    assert result.currency == "USD"


def test_get_tenant_budget_not_found_raises() -> None:
    """Verify querying non-existent tenant raises TenantNotFoundError."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = GetTenantBudgetQueryHandler(unit_of_work=uow)

    with pytest.raises(TenantNotFoundError, match="no encontrado"):
        handler.handle(GetTenantBudgetQuery(tenant_id="non-existent"))
