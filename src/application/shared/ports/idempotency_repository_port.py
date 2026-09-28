"""Port for Idempotency Repository in Application Layer.

Rules:
- Belongs to src/application/shared/ports/.
- Defines the contract for atomic acquisition and cached execution results of commands.
- Agnostic to databases (SQL Server, Redis, In-Memory).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class IdempotencyStatus(StrEnum):
    """Lifecycle states for an idempotency record."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class IdempotencyRecord:
    """Immutable record storing prior execution response for a request."""

    key: str
    status: IdempotencyStatus
    response_code: int | None = None
    response_body: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IdempotencyRepositoryPort(ABC):
    """Abstract port for idempotency persistence and locking."""

    @abstractmethod
    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        """Attempt to acquire execution lock for key.

        Returns:
            True if key was unreserved and is now locked; False if already in-flight or completed.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> IdempotencyRecord | None:
        """Retrieve idempotency record by key, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, Any]
    ) -> None:
        """Store the successful response payload for subsequent idempotent re-issues."""
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(self, key: str, error_message: str) -> None:
        """Mark record as failed so controlled retry policies can proceed."""
        raise NotImplementedError
