"""Template canónico para el Puerto del Repositorio de Idempotencia (Application Port).

Reglas:
- Pertenece a src/application/shared/ports/.
- Define el contrato para control de concurrencia y deduplicación atómica de comandos.
- Desacoplado de SQLAlchemy, Redis o bases de datos específicas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class IdempotencyStatus(str, Enum):
    """Estados del ciclo de vida de un registro de idempotencia."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class IdempotencyRecord:
    """Registro inmutable que contiene el estado y resultado previo de una petición."""

    key: str
    status: IdempotencyStatus
    response_code: int | None = None
    response_body: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IdempotencyRepositoryPort(ABC):
    """Puerto para persistencia y adquisición atómica de claves de idempotencia."""

    @abstractmethod
    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        """Intenta adquirir el lock para la clave. Retorna True si es nueva y fue reservada; False si ya existe."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> IdempotencyRecord | None:
        """Obtiene el registro de idempotencia asociado a la clave, o None si no existe."""
        raise NotImplementedError

    @abstractmethod
    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, Any]
    ) -> None:
        """Almacena la respuesta exitosa para reemisiones idempotentes."""
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(self, key: str, error_message: str) -> None:
        """Marca la clave como fallida para permitir reintentos posteriores controlados."""
        raise NotImplementedError
