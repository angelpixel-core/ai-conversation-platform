"""Template canónico para InMemoryIdempotencyRepositoryAdapter.

Reglas:
- Pertenece a src/infrastructure/persistence/in_memory/.
- Implementa IdempotencyRepositoryPort.
- Provee almacenamiento en memoria thread-safe/task-safe para tests unitarios y desarrollo local.
"""

from datetime import datetime, timezone
from typing import Any

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)


class InMemoryIdempotencyRepositoryAdapter(IdempotencyRepositoryPort):
    """Adaptador en memoria para el repositorio de idempotencia."""

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}

    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        if key in self._records:
            return False

        now = datetime.now(timezone.utc)
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
            now = datetime.now(timezone.utc)
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
            now = datetime.now(timezone.utc)
            self._records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.FAILED,
                response_body={"error": error_message},
                created_at=self._records[key].created_at,
                updated_at=now,
            )
