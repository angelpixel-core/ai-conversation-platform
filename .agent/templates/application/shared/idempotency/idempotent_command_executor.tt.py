"""Template canónico para IdempotentCommandExecutor (Application Pipeline/Service).

Reglas:
- Pertenece a src/application/shared/idempotency/.
- Envuelve la ejecución de comandos para garantizar deduplicación distribuida.
- Si el comando ya fue completado para la clave, retorna el resultado cacheado.
- Si una ejecución con la misma clave está en curso, previene concurrencia no deseada.
"""

from collections.abc import Awaitable, Callable
import logging
from typing import Any, TypeVar

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class IdempotencyConflictError(Exception):
    """Excepción lanzada cuando una operación idéntica ya está en proceso de ejecución."""

    pass


class IdempotentCommandExecutor:
    """Orquestador que asegura la ejecución idempotente de comandos asíncronos."""

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
        """Ejecuta la operación de forma idempotente si se proporciona una clave."""
        if not key:
            return await operation()

        existing = await self._repo.get(key)
        if existing and existing.status == IdempotencyStatus.COMPLETED:
            logger.info("Retornando resultado idempotente cacheado para clave: %s", key)
            if response_deserializer and existing.response_body:
                return response_deserializer(existing.response_body)
            return existing.response_body  # type: ignore[return-value]

        acquired = await self._repo.try_acquire(key, ttl_seconds=self._ttl)
        if not acquired:
            logger.warning(
                "Conflicto de idempotencia: clave %s en ejecución simultánea", key
            )
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
            await self._repo.mark_completed(
                key=key, response_code=200, response_body=serialized
            )
            return result
        except Exception as exc:
            await self._repo.mark_failed(key=key, error_message=str(exc))
            raise
