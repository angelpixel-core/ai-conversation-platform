"""Test template canónico para IdempotentCommandExecutor."""

import pytest

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)
from .idempotent_command_executor import (
    IdempotencyConflictError,
    IdempotentCommandExecutor,
)


class FakeIdempotencyRepo(IdempotencyRepositoryPort):
    def __init__(self) -> None:
        self.store: dict[str, IdempotencyRecord] = {}

    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        if key in self.store:
            return False
        self.store[key] = IdempotencyRecord(key=key, status=IdempotencyStatus.PENDING)
        return True

    async def get(self, key: str) -> IdempotencyRecord | None:
        return self.store.get(key)

    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, str]
    ) -> None:
        self.store[key] = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.COMPLETED,
            response_code=response_code,
            response_body=response_body,
        )

    async def mark_failed(self, key: str, error_message: str) -> None:
        self.store[key] = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.FAILED,
            response_body={"error": error_message},
        )


@pytest.mark.anyio
async def test_idempotent_executor_runs_operation_first_time() -> None:
    repo = FakeIdempotencyRepo()
    executor = IdempotentCommandExecutor(idempotency_repo=repo)

    called_count = 0

    async def sample_op() -> dict[str, str]:
        nonlocal called_count
        called_count += 1
        return {"data": "success"}

    res = await executor.execute("key-abc", sample_op)
    assert res == {"data": "success"}
    assert called_count == 1

    # Segunda invocación con la misma clave debe retornar resultado en cache y no volver a invocar la operación
    cached_res = await executor.execute("key-abc", sample_op)
    assert cached_res == {"data": "success"}
    assert called_count == 1


@pytest.mark.anyio
async def test_idempotent_executor_raises_on_concurrent_pending() -> None:
    repo = FakeIdempotencyRepo()
    await repo.try_acquire("key-pending")

    executor = IdempotentCommandExecutor(idempotency_repo=repo)

    async def sample_op() -> dict[str, str]:
        return {"data": "success"}

    with pytest.raises(IdempotencyConflictError, match="ya se encuentra en procesamiento"):
        await executor.execute("key-pending", sample_op)
