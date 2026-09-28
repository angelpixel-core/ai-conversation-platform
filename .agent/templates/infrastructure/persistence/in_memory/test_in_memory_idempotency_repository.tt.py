"""Test template canónico para InMemoryIdempotencyRepositoryAdapter."""

import pytest

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)
from .in_memory_idempotency_repository import (
    InMemoryIdempotencyRepositoryAdapter,
)


@pytest.mark.anyio
async def test_in_memory_idempotency_repository_lifecycle() -> None:
    repo = InMemoryIdempotencyRepositoryAdapter()
    assert isinstance(repo, IdempotencyRepositoryPort)

    key = "idem-test-123"
    # Adquisición inicial
    acquired = await repo.try_acquire(key)
    assert acquired is True

    # Reintento simultáneo debe fallar
    second_acquire = await repo.try_acquire(key)
    assert second_acquire is False

    # Consulta de estado pendiente
    rec = await repo.get(key)
    assert rec is not None
    assert rec.status == IdempotencyStatus.PENDING

    # Marcar completado
    await repo.mark_completed(key, 201, {"status": "created"})
    completed = await repo.get(key)
    assert completed is not None
    assert completed.status == IdempotencyStatus.COMPLETED
    assert completed.response_code == 201
    assert completed.response_body == {"status": "created"}


@pytest.mark.anyio
async def test_in_memory_idempotency_repository_mark_failed() -> None:
    repo = InMemoryIdempotencyRepositoryAdapter()
    key = "idem-fail-test"
    await repo.try_acquire(key)
    await repo.mark_failed(key, "DB Connection Timeout")

    rec = await repo.get(key)
    assert rec is not None
    assert rec.status == IdempotencyStatus.FAILED
    assert rec.response_body == {"error": "DB Connection Timeout"}
