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

from src.application.shared.exceptions import (
    IdempotencyConflictError,
    IdempotencyPayloadMismatchError,
)
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
        self._fingerprints: dict[str, str] = {}

    async def execute(
        self,
        key: str | None,
        operation: Callable[[], Awaitable[T]],
        response_serializer: Callable[[T], dict[str, Any]] | None = None,
        response_deserializer: Callable[[dict[str, Any]], T] | None = None,
        payload_fingerprint: str | None = None,
        on_cache_hit: Callable[[T], T] | None = None,
    ) -> T:
        """Executes the operation idempotently if a key is provided."""
        if not key:
            return await operation()

        existing = await self._repo.get(key)
        stored_fingerprint = self._fingerprints.get(key)
        if (
            existing
            and isinstance(existing.response_body, dict)
            and "_payload_fingerprint" in existing.response_body
        ):
            stored_fingerprint = str(existing.response_body["_payload_fingerprint"])

        if (
            payload_fingerprint is not None
            and stored_fingerprint is not None
            and stored_fingerprint != payload_fingerprint
        ):
            logger.warning("Idempotency payload mismatch for key: %s", key)
            raise IdempotencyPayloadMismatchError(
                f"La clave de idempotencia '{key}' fue reutilizada con un payload diferente."
            )

        if existing and existing.status == IdempotencyStatus.COMPLETED:
            logger.info("Returning cached idempotent result for key: %s", key)
            body = existing.response_body
            if isinstance(body, dict) and "_payload_fingerprint" in body:
                body = {k: v for k, v in body.items() if k != "_payload_fingerprint"}
            if response_deserializer and body:
                deserialized = response_deserializer(body)
                return on_cache_hit(deserialized) if on_cache_hit is not None else deserialized
            cached_val: T = body  # type: ignore[assignment]
            return on_cache_hit(cached_val) if on_cache_hit is not None else cached_val

        acquired = await self._repo.try_acquire(key, ttl_seconds=self._ttl)
        if not acquired:
            if (
                payload_fingerprint is not None
                and key in self._fingerprints
                and self._fingerprints[key] != payload_fingerprint
            ):
                raise IdempotencyPayloadMismatchError(
                    f"La clave de idempotencia '{key}' fue reutilizada con un payload diferente."
                )
            logger.warning("Idempotency conflict: key %s already being processed", key)
            raise IdempotencyConflictError(
                f"La solicitud con Idempotency-Key '{key}' ya se encuentra en procesamiento."
            )

        if payload_fingerprint is not None:
            self._fingerprints[key] = payload_fingerprint

        try:
            result = await operation()
            serialized = (
                response_serializer(result)
                if response_serializer
                else (result if isinstance(result, dict) else {"result": str(result)})
            )
            if payload_fingerprint is not None and isinstance(serialized, dict):
                serialized = {**serialized, "_payload_fingerprint": payload_fingerprint}
            await self._repo.mark_completed(key=key, response_code=200, response_body=serialized)
            return result
        except Exception as exc:
            self._fingerprints.pop(key, None)
            await self._repo.mark_failed(key=key, error_message=str(exc))
            raise


__all__ = [
    "IdempotencyConflictError",
    "IdempotencyPayloadMismatchError",
    "IdempotentCommandExecutor",
]
