"""Integration tests for MssqlIdempotencyRepositoryAdapter against live SQL Server."""

import pytest
from sqlalchemy.engine import Engine

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyStatus,
)
from src.infrastructure.persistence.mssql.connection import (
    create_session_factory,
)
from src.infrastructure.persistence.mssql.idempotency_repository import (
    MssqlIdempotencyRepositoryAdapter,
)


@pytest.mark.anyio
async def test_mssql_idempotency_repository_lifecycle_real_db(
    mssql_engine: Engine, clean_db: None
) -> None:
    session_factory = create_session_factory(mssql_engine)
    key = "real-mssql-idem-key"

    with session_factory() as session:
        repo = MssqlIdempotencyRepositoryAdapter(session=session)
        acquired = await repo.try_acquire(key)
        assert acquired is True

    # Duplicate acquisition in new session fails
    with session_factory() as session:
        repo = MssqlIdempotencyRepositoryAdapter(session=session)
        second_acquire = await repo.try_acquire(key)
        assert second_acquire is False

    # Mark completed in new session
    with session_factory() as session:
        repo = MssqlIdempotencyRepositoryAdapter(session=session)
        await repo.mark_completed(key, 201, {"resource_id": "abc-123"})

    # Query completed in new session
    with session_factory() as session:
        repo = MssqlIdempotencyRepositoryAdapter(session=session)
        rec = await repo.get(key)
        assert rec is not None
        assert rec.status == IdempotencyStatus.COMPLETED
        assert rec.response_code == 201
        assert rec.response_body == {"resource_id": "abc-123"}
