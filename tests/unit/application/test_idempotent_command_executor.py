"""Unit tests for IdempotentCommandExecutor."""

from typing import Any

import pytest
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotencyConflictError,
    IdempotentCommandExecutor,
)

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
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
        self, key: str, response_code: int, response_body: dict[str, Any]
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

    # Second invocation with same key returns cached result without running operation
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


@pytest.mark.anyio
async def test_idempotent_executor_skips_idempotency_when_key_is_none() -> None:
    repo = FakeIdempotencyRepo()
    executor = IdempotentCommandExecutor(idempotency_repo=repo)

    called_count = 0

    async def sample_op() -> dict[str, str]:
        nonlocal called_count
        called_count += 1
        return {"data": "no-key"}

    res1 = await executor.execute(None, sample_op)
    res2 = await executor.execute(None, sample_op)

    assert res1 == {"data": "no-key"}
    assert res2 == {"data": "no-key"}
    assert called_count == 2
    assert len(repo.store) == 0


@pytest.mark.anyio
async def test_idempotent_executor_custom_serializer_and_deserializer() -> None:
    repo = FakeIdempotencyRepo()
    executor = IdempotentCommandExecutor(idempotency_repo=repo)

    class CustomResponse:
        def __init__(self, value: int) -> None:
            self.value = value

    async def sample_op() -> CustomResponse:
        return CustomResponse(42)

    res = await executor.execute(
        "custom-key",
        sample_op,
        response_serializer=lambda r: {"val": r.value},
        response_deserializer=lambda d: CustomResponse(d["val"]),
    )
    assert isinstance(res, CustomResponse)
    assert res.value == 42

    # Cached invocation uses deserializer
    cached = await executor.execute(
        "custom-key",
        sample_op,
        response_serializer=lambda r: {"val": r.value},
        response_deserializer=lambda d: CustomResponse(d["val"]),
    )
    assert isinstance(cached, CustomResponse)
    assert cached.value == 42


@pytest.mark.anyio
async def test_idempotent_executor_marks_failed_on_exception() -> None:
    repo = FakeIdempotencyRepo()
    executor = IdempotentCommandExecutor(idempotency_repo=repo)

    async def faulty_op() -> dict[str, str]:
        raise RuntimeError("Something went wrong")

    with pytest.raises(RuntimeError, match="Something went wrong"):
        await executor.execute("fail-key", faulty_op)

    rec = await repo.get("fail-key")
    assert rec is not None
    assert rec.status == IdempotencyStatus.FAILED
    assert rec.response_body == {"error": "Something went wrong"}
