"""Unit tests for MssqlTenantRepositoryAdapter adapter."""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.tenant_repository import MssqlTenantRepositoryAdapter


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_repository_add_and_get(sqlite_session: Session) -> None:
    repo = MssqlTenantRepositoryAdapter(session=sqlite_session)
    tenant = Tenant(
        tenant_id=TenantId("tenant-alpha"),
        name="Tenant Alpha",
        budget=MonetaryBudget(balance=Decimal("100.0000"), reserved_amount=Decimal("10.0000")),
        policy=TenantPolicy(
            tier=TenantTier.STANDARD,
            max_tokens_per_request=4096,
            monthly_budget_usd=Decimal("200.0000"),
            allowed_models=frozenset({"gpt-4o-mini", "gemini-1.5-flash"}),
        ),
    )

    repo.add(tenant)
    sqlite_session.commit()

    retrieved = repo.get(TenantId("tenant-alpha"))
    assert retrieved is not None
    assert retrieved.id.value == "tenant-alpha"
    assert retrieved.name == "Tenant Alpha"
    assert retrieved.budget.balance == Decimal("100.0000")
    assert retrieved.budget.reserved_amount == Decimal("10.0000")
    assert retrieved.policy.tier == TenantTier.STANDARD
    assert "gpt-4o-mini" in retrieved.policy.allowed_models


def test_repository_get_not_found(sqlite_session: Session) -> None:
    repo = MssqlTenantRepositoryAdapter(session=sqlite_session)
    retrieved = repo.get(TenantId("nonexistent-tenant"))
    assert retrieved is None


def test_repository_get_for_update(sqlite_session: Session) -> None:
    repo = MssqlTenantRepositoryAdapter(session=sqlite_session)
    tenant = Tenant(
        tenant_id=TenantId("tenant-lock"),
        name="Tenant Lock Test",
        budget=MonetaryBudget(balance=Decimal("500.0000")),
    )
    repo.add(tenant)
    sqlite_session.commit()

    locked_tenant = repo.get_for_update(TenantId("tenant-lock"))
    assert locked_tenant is not None
    assert locked_tenant.id.value == "tenant-lock"
    assert locked_tenant.budget.balance == Decimal("500.0000")


def test_repository_list_tenants(sqlite_session: Session) -> None:
    repo = MssqlTenantRepositoryAdapter(session=sqlite_session)
    t1 = Tenant(
        tenant_id=TenantId("tenant-1"),
        name="Tenant One",
        budget=MonetaryBudget(balance=Decimal("10.0000")),
    )
    t2 = Tenant(
        tenant_id=TenantId("tenant-2"),
        name="Tenant Two",
        budget=MonetaryBudget(balance=Decimal("20.0000")),
    )
    repo.add(t1)
    repo.add(t2)
    sqlite_session.commit()

    all_tenants = repo.list()
    assert len(all_tenants) >= 2
    ids = [t.id.value for t in all_tenants]
    assert "tenant-1" in ids
    assert "tenant-2" in ids


def test_repository_update_existing_tenant(sqlite_session: Session) -> None:
    repo = MssqlTenantRepositoryAdapter(session=sqlite_session)
    tenant = Tenant(
        tenant_id=TenantId("tenant-update"),
        name="Original Name",
        budget=MonetaryBudget(balance=Decimal("100.0000")),
        status=TenantStatus.ACTIVE,
    )
    repo.add(tenant)
    sqlite_session.commit()

    # Modify balance and status
    tenant.reserve_budget(Decimal("30.0000"), "gpt-4o-mini")
    repo.add(tenant)
    sqlite_session.commit()

    reloaded = repo.get(TenantId("tenant-update"))
    assert reloaded is not None
    assert reloaded.budget.reserved_amount == Decimal("30.0000")
    assert reloaded.budget.available_balance == Decimal("70.0000")
