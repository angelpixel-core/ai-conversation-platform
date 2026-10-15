"""Unit tests for ListTenantsQuery and ListTenantsQueryHandler."""

from datetime import UTC, datetime
from decimal import Decimal

from src.application.tenants.queries.list_tenants_query import (
    ListTenantsQuery,
    ListTenantsQueryHandler,
)
from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_list_tenants_empty() -> None:
    """Verify handler returns empty list when no tenants exist."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = ListTenantsQueryHandler(unit_of_work=uow)

    results = handler.handle(ListTenantsQuery())
    assert results == []


def test_list_tenants_returns_flattened_and_enriched_dto() -> None:
    """Verify projection provides both root flattened figures and RFC-32 sub-structures."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = ListTenantsQueryHandler(unit_of_work=uow)

    t1 = Tenant(
        tenant_id=TenantId("corp-acme"),
        name="ACME Corporation",
        budget=MonetaryBudget(
            balance=Decimal("1000.00"),
            reserved_amount=Decimal("100.00"),
            currency="USD",
        ),
        policy=TenantPolicy.default_for_tier(TenantTier.ENTERPRISE),
        status=TenantStatus.ACTIVE,
        contact_email="ops@acme.corp",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    with uow:
        uow.tenants.add(t1)
        uow.commit()

    results = handler.handle(ListTenantsQuery())
    assert len(results) == 1
    dto = results[0]

    # Dual identifier check
    assert dto.id == "corp-acme"
    assert dto.tenant_id == "corp-acme"
    assert dto.name == "ACME Corporation"
    assert dto.status == "ACTIVE"
    assert dto.tier == "ENTERPRISE"

    # Flattened backwards-compatibility fields
    assert dto.balance == Decimal("1000.00")
    assert dto.reserved_amount == Decimal("100.00")
    assert dto.available_balance == Decimal("900.00")
    assert dto.currency == "USD"

    # Structured RFC-32 fields
    assert dto.financials.currency == "USD"
    assert dto.financials.balance == Decimal("1000.00")
    assert dto.financials.reserved_amount == Decimal("100.00")
    assert dto.financials.available_balance == Decimal("900.00")
    assert dto.financials.monthly_budget_usd == Decimal("10000.00")

    assert dto.limits.max_tokens_per_request == 16384
    assert dto.limits.max_requests_per_minute == 300

    assert dto.metadata.contact_email == "ops@acme.corp"
    assert dto.metadata.created_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert dto.metadata.updated_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_list_tenants_filters_by_status() -> None:
    """Verify status filter properly segments active and suspended tenants."""
    uow = InMemoryUnitOfWorkAdapter()
    handler = ListTenantsQueryHandler(unit_of_work=uow)

    t_active = Tenant(
        tenant_id=TenantId("corp-active"),
        name="Active Corp",
        budget=MonetaryBudget(balance=Decimal("50.00")),
        status=TenantStatus.ACTIVE,
    )
    t_suspended = Tenant(
        tenant_id=TenantId("corp-suspended"),
        name="Suspended Corp",
        budget=MonetaryBudget(balance=Decimal("0.00")),
        status=TenantStatus.SUSPENDED,
    )
    with uow:
        uow.tenants.add(t_active)
        uow.tenants.add(t_suspended)
        uow.commit()

    active_only = handler.handle(ListTenantsQuery(status="ACTIVE"))
    assert len(active_only) == 1
    assert active_only[0].id == "corp-active"

    suspended_only = handler.handle(ListTenantsQuery(status="SUSPENDED"))
    assert len(suspended_only) == 1
    assert suspended_only[0].id == "corp-suspended"
