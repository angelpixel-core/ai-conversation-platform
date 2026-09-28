"""Integration tests for concurrent budget reservations with pessimistic locking."""

import threading
from decimal import Decimal

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine
from src.infrastructure.persistence.mssql.tenant_repository import MssqlTenantRepository

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.connection import create_session_factory


def test_concurrent_reservations_prevent_overdraft_sqlite() -> None:
    """Validate that sequential / concurrent transactions cannot overspend the budget."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    # 1. Initialize tenant with $10.00 balance
    with Session(engine) as session:
        repo = MssqlTenantRepository(session=session)
        tenant = Tenant(
            tenant_id=TenantId("race-tenant"),
            name="Race Tenant",
            budget=MonetaryBudget(balance=Decimal("10.0000")),
        )
        repo.add(tenant)
        session.commit()

    # 2. Attempt two $8.00 reservations
    results: list[bool] = []

    def attempt_reservation(cost: Decimal) -> None:
        with Session(engine) as session:
            repo = MssqlTenantRepository(session=session)
            t = repo.get_for_update(TenantId("race-tenant"))
            if t is None:
                results.append(False)
                return
            try:
                t.reserve_budget(cost, "gpt-4o-mini")
                repo.add(t)
                session.commit()
                results.append(True)
            except ValueError:
                session.rollback()
                results.append(False)

    attempt_reservation(Decimal("8.0000"))
    attempt_reservation(Decimal("8.0000"))

    # Exactly one must succeed, one must fail
    assert results == [True, False]

    # Verify final state: balance $10.00, reserved $8.00, available $2.00
    with Session(engine) as session:
        repo = MssqlTenantRepository(session=session)
        final_t = repo.get(TenantId("race-tenant"))
        assert final_t is not None
        assert final_t.budget.balance == Decimal("10.0000")
        assert final_t.budget.reserved_amount == Decimal("8.0000")
        assert final_t.budget.available_balance == Decimal("2.0000")


def test_concurrent_threads_reservation_simulation() -> None:
    """Validate multi-threaded race simulation ensuring only valid reservations commit."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = MssqlTenantRepository(session=session)
        tenant = Tenant(
            tenant_id=TenantId("threaded-tenant"),
            name="Threaded Tenant",
            budget=MonetaryBudget(balance=Decimal("15.0000")),
        )
        repo.add(tenant)
        session.commit()

    outcomes: list[bool] = []
    lock = threading.Lock()

    def worker_reserve() -> None:
        with Session(engine) as session:
            repo = MssqlTenantRepository(session=session)
            with lock:
                t = repo.get_for_update(TenantId("threaded-tenant"))
                if t and t.budget.can_reserve(Decimal("10.0000")):
                    t.reserve_budget(Decimal("10.0000"), "gpt-4o-mini")
                    repo.add(t)
                    session.commit()
                    outcomes.append(True)
                else:
                    outcomes.append(False)

    t1 = threading.Thread(target=worker_reserve)
    t2 = threading.Thread(target=worker_reserve)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One succeeds, one fails because $15 < $10 + $10
    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 1


def test_concurrent_reservations_live_mssql(mssql_engine: Engine, clean_db: None) -> None:
    """Test concurrent rowlock reservations on live MSSQL Server if present."""
    session_factory = create_session_factory(mssql_engine)

    with session_factory() as session:
        repo = MssqlTenantRepository(session=session)
        tenant = Tenant(
            tenant_id=TenantId("mssql-lock-tenant"),
            name="MSSQL Lock Tenant",
            budget=MonetaryBudget(balance=Decimal("10.0000")),
        )
        repo.add(tenant)
        session.commit()

    # Try two reservations
    successes = 0
    failures = 0
    for _ in range(2):
        with session_factory() as session:
            repo = MssqlTenantRepository(session=session)
            t = repo.get_for_update(TenantId("mssql-lock-tenant"))
            if t and t.budget.can_reserve(Decimal("7.0000")):
                t.reserve_budget(Decimal("7.0000"), "gpt-4o-mini")
                repo.add(t)
                session.commit()
                successes += 1
            else:
                failures += 1

    assert successes == 1
    assert failures == 1
