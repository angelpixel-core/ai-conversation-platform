"""Unit tests for MssqlIdempotencyRepositoryAdapter adapter."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)
from src.infrastructure.persistence.mssql.idempotency_repository import (
    MssqlIdempotencyRepositoryAdapter,
)


@pytest.fixture(name="session")
def fixture_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.mark.anyio
async def test_mssql_idempotency_repository_lifecycle(session: Session) -> None:
    repo = MssqlIdempotencyRepositoryAdapter(session=session)
    assert isinstance(repo, IdempotencyRepositoryPort)

    key = "idem-mssql-123"

    # Initial acquisition succeeds
    acquired = await repo.try_acquire(key)
    assert acquired is True

    # Duplicate acquisition fails
    second = await repo.try_acquire(key)
    assert second is False

    # Lookup
    rec = await repo.get(key)
    assert rec is not None
    assert rec.status == IdempotencyStatus.PENDING

    # Mark completed
    await repo.mark_completed(key, 200, {"success": True})
    completed = await repo.get(key)
    assert completed is not None
    assert completed.status == IdempotencyStatus.COMPLETED
    assert completed.response_code == 200
    assert completed.response_body == {"success": True}


@pytest.mark.anyio
async def test_mssql_idempotency_repository_mark_failed(session: Session) -> None:
    repo = MssqlIdempotencyRepositoryAdapter(session=session)
    key = "idem-fail-mssql"

    await repo.try_acquire(key)
    await repo.mark_failed(key, "DB Error")

    failed = await repo.get(key)
    assert failed is not None
    assert failed.status == IdempotencyStatus.FAILED
    assert failed.response_body == {"error": "DB Error"}
