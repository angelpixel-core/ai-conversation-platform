"""In-memory implementation of the IdempotencyRepositoryPort.

Rules:
- Belongs to src/infrastructure/persistence/in_memory/.
- Implements IdempotencyRepositoryPort.
- Provides task-safe in-memory storage for unit tests and local development.
"""

from datetime import UTC, datetime
from typing import Any

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)


class InMemoryIdempotencyRepositoryAdapter(IdempotencyRepositoryPort):
    """In-memory adapter for the idempotency repository port."""

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}

    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        if key in self._records:
            return False

        now = datetime.now(UTC)
        self._records[key] = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        return True

    async def get(self, key: str) -> IdempotencyRecord | None:
        return self._records.get(key)

    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, Any]
    ) -> None:
        if key in self._records:
            now = datetime.now(UTC)
            self._records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.COMPLETED,
                response_code=response_code,
                response_body=response_body,
                created_at=self._records[key].created_at,
                updated_at=now,
            )

    async def mark_failed(self, key: str, error_message: str) -> None:
        if key in self._records:
            now = datetime.now(UTC)
            self._records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.FAILED,
                response_body={"error": error_message},
                created_at=self._records[key].created_at,
                updated_at=now,
            )


__all__ = ["InMemoryIdempotencyRepositoryAdapter"]
