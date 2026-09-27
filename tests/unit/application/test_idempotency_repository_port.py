"""Unit contract tests for IdempotencyRepositoryPort."""

from datetime import UTC, datetime
from typing import Any

import pytest
from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)


class FakeIdempotencyRepository(IdempotencyRepositoryPort):
    """Fake in-memory repository to test adherence to IdempotencyRepositoryPort contract."""

    def __init__(self) -> None:
        self.records: dict[str, IdempotencyRecord] = {}

    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        if key in self.records:
            return False
        self.records[key] = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        return True

    async def get(self, key: str) -> IdempotencyRecord | None:
        return self.records.get(key)

    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, Any]
    ) -> None:
        if key in self.records:
            self.records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.COMPLETED,
                response_code=response_code,
                response_body=response_body,
                updated_at=datetime.now(UTC),
            )

    async def mark_failed(self, key: str, error_message: str) -> None:
        if key in self.records:
            self.records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.FAILED,
                response_body={"error": error_message},
                updated_at=datetime.now(UTC),
            )


@pytest.mark.anyio
async def test_idempotency_repository_port_contract() -> None:
    repo = FakeIdempotencyRepository()
    assert isinstance(repo, IdempotencyRepositoryPort)

    acquired = await repo.try_acquire("req-1")
    assert acquired is True

    # Duplicate acquisition must fail
    duplicate = await repo.try_acquire("req-1")
    assert duplicate is False

    record = await repo.get("req-1")
    assert record is not None
    assert record.status == IdempotencyStatus.PENDING
    assert record.key == "req-1"

    await repo.mark_completed("req-1", 200, {"id": "res-123"})
    completed = await repo.get("req-1")
    assert completed is not None
    assert completed.status == IdempotencyStatus.COMPLETED
    assert completed.response_code == 200
    assert completed.response_body == {"id": "res-123"}


@pytest.mark.anyio
async def test_idempotency_repository_port_mark_failed() -> None:
    repo = FakeIdempotencyRepository()
    await repo.try_acquire("req-fail")
    await repo.mark_failed("req-fail", "Timeout error")

    failed = await repo.get("req-fail")
    assert failed is not None
    assert failed.status == IdempotencyStatus.FAILED
    assert failed.response_body == {"error": "Timeout error"}
