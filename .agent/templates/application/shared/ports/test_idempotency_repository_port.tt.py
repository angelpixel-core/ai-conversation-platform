"""Test template canónico para IdempotencyRepositoryPort y Value Objects asociados."""

from datetime import datetime, timezone
import pytest

from .idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)


class FakeIdempotencyRepository(IdempotencyRepositoryPort):
    """Implementación de prueba para verificar cumplimiento del puerto."""

    def __init__(self) -> None:
        self.records: dict[str, IdempotencyRecord] = {}

    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        if key in self.records:
            return False
        self.records[key] = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        return True

    async def get(self, key: str) -> IdempotencyRecord | None:
        return self.records.get(key)

    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, str]
    ) -> None:
        if key in self.records:
            self.records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.COMPLETED,
                response_code=response_code,
                response_body=response_body,
                updated_at=datetime.now(timezone.utc),
            )

    async def mark_failed(self, key: str, error_message: str) -> None:
        if key in self.records:
            self.records[key] = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.FAILED,
                response_body={"error": error_message},
                updated_at=datetime.now(timezone.utc),
            )


@pytest.mark.anyio
async def test_fake_idempotency_repository_implements_contract() -> None:
    repo = FakeIdempotencyRepository()
    assert isinstance(repo, IdempotencyRepositoryPort)

    acquired = await repo.try_acquire("key-1")
    assert acquired is True

    # Segundo intento con la misma clave debe ser rechazado
    duplicate = await repo.try_acquire("key-1")
    assert duplicate is False

    record = await repo.get("key-1")
    assert record is not None
    assert record.status == IdempotencyStatus.PENDING

    await repo.mark_completed("key-1", 200, {"id": "res-123"})
    completed = await repo.get("key-1")
    assert completed is not None
    assert completed.status == IdempotencyStatus.COMPLETED
    assert completed.response_code == 200
    assert completed.response_body == {"id": "res-123"}
