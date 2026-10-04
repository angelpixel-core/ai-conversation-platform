"""IdempotentCommandExecutor application service/pipeline.

Rules:
- Belongs to src/application/shared/idempotency/.
- Wraps command execution to provide distributed idempotency.
- If command has completed for this key, returns cached response.
- If execution is currently pending/in progress for this key, raises IdempotencyConflictError.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from src.application.shared.exceptions import IdempotencyConflictError
from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class IdempotentCommandExecutor:
    """Orchestrator ensuring idempotent execution of asynchronous commands."""

    def __init__(
        self,
        idempotency_repo: IdempotencyRepositoryPort,
        lock_ttl_seconds: int = 120,
    ) -> None:
        self._repo = idempotency_repo
        self._ttl = lock_ttl_seconds

    async def execute(
        self,
        key: str | None,
        operation: Callable[[], Awaitable[T]],
        response_serializer: Callable[[T], dict[str, Any]] | None = None,
        response_deserializer: Callable[[dict[str, Any]], T] | None = None,
    ) -> T:
        """Executes the operation idempotently if a key is provided."""
        if not key:
            return await operation()

        existing = await self._repo.get(key)
        if existing and existing.status == IdempotencyStatus.COMPLETED:
            logger.info("Returning cached idempotent result for key: %s", key)
            if response_deserializer and existing.response_body:
                return response_deserializer(existing.response_body)
            return existing.response_body  # type: ignore[return-value]

        acquired = await self._repo.try_acquire(key, ttl_seconds=self._ttl)
        if not acquired:
            logger.warning("Idempotency conflict: key %s already being processed", key)
            raise IdempotencyConflictError(
                f"La solicitud con Idempotency-Key '{key}' ya se encuentra en procesamiento."
            )

        try:
            result = await operation()
            serialized = (
                response_serializer(result)
                if response_serializer
                else (result if isinstance(result, dict) else {"result": str(result)})
            )
            await self._repo.mark_completed(key=key, response_code=200, response_body=serialized)
            return result
        except Exception as exc:
            await self._repo.mark_failed(key=key, error_message=str(exc))
            raise
