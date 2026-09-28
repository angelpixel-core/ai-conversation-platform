"""Integration tests for multi-tenant data isolation and scoping."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.connection import create_session_factory
from src.infrastructure.persistence.mssql.models import ConversationModel
from src.infrastructure.persistence.mssql.tenant_repository import MssqlTenantRepository


def test_tenant_isolation_conversations_sqlite() -> None:
    """Validate query filtering isolation across tenants in a relational session."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conv_a = ConversationModel(
        id=uuid4(),
        title="Tenant A Conversation",
        tenant_id="tenant-a",
    )
    conv_b = ConversationModel(
        id=uuid4(),
        title="Tenant B Conversation",
        tenant_id="tenant-b",
    )

    with Session(engine) as session:
        session.add(conv_a)
        session.add(conv_b)
        session.commit()

    with Session(engine) as session:
        tenant_a_convs = session.exec(
            select(ConversationModel).where(ConversationModel.tenant_id == "tenant-a")
        ).all()
        assert len(tenant_a_convs) == 1
        assert tenant_a_convs[0].title == "Tenant A Conversation"
        assert tenant_a_convs[0].tenant_id == "tenant-a"

        tenant_b_convs = session.exec(
            select(ConversationModel).where(ConversationModel.tenant_id == "tenant-b")
        ).all()
        assert len(tenant_b_convs) == 1
        assert tenant_b_convs[0].title == "Tenant B Conversation"
        assert tenant_b_convs[0].tenant_id == "tenant-b"


def test_tenant_isolation_budget_sqlite() -> None:
    """Validate budget mutations on Tenant A do not mutate Tenant B."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = MssqlTenantRepository(session=session)
        t_a = Tenant(
            tenant_id=TenantId("tenant-a"),
            name="Tenant A",
            budget=MonetaryBudget(balance=Decimal("100.0000")),
        )
        t_b = Tenant(
            tenant_id=TenantId("tenant-b"),
            name="Tenant B",
            budget=MonetaryBudget(balance=Decimal("200.0000")),
        )
        repo.add(t_a)
        repo.add(t_b)
        session.commit()

    with Session(engine) as session:
        repo = MssqlTenantRepository(session=session)
        loaded_a = repo.get_for_update(TenantId("tenant-a"))
        assert loaded_a is not None
        loaded_a.reserve_budget(Decimal("40.0000"), "gpt-4o-mini")
        repo.add(loaded_a)
        session.commit()

    with Session(engine) as session:
        repo = MssqlTenantRepository(session=session)
        re_a = repo.get(TenantId("tenant-a"))
        re_b = repo.get(TenantId("tenant-b"))

        assert re_a is not None and re_a.budget.available_balance == Decimal("60.0000")
        assert re_b is not None and re_b.budget.available_balance == Decimal("200.0000")


def test_mssql_tenant_isolation_live(mssql_engine: Engine, clean_db: None) -> None:
    """Validate multi-tenant isolation against live MSSQL instance if available."""
    session_factory = create_session_factory(mssql_engine)

    with session_factory() as session:
        repo = MssqlTenantRepository(session=session)
        t1 = Tenant(
            tenant_id=TenantId("live-t1"), name="Live T1", budget=MonetaryBudget(Decimal("50.00"))
        )
        t2 = Tenant(
            tenant_id=TenantId("live-t2"), name="Live T2", budget=MonetaryBudget(Decimal("80.00"))
        )
        repo.add(t1)
        repo.add(t2)
        session.commit()

    with session_factory() as session:
        repo = MssqlTenantRepository(session=session)
        t1_loaded = repo.get(TenantId("live-t1"))
        t2_loaded = repo.get(TenantId("live-t2"))

        assert t1_loaded is not None and t1_loaded.budget.balance == Decimal("50.0000")
        assert t2_loaded is not None and t2_loaded.budget.balance == Decimal("80.0000")
