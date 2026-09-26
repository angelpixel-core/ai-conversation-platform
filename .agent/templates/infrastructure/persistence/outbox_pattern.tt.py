"""
Template canónico para el Patrón Transactional Outbox & Dispatcher Worker.
Reglas:
- Modelo de mensaje de Outbox registrado en la misma transacción que los agregados de dominio.
- Dispatcher asíncrono que sondea o reacciona para procesar eventos pendientes.
- Marcado de eventos procesados o fallidos con registro de reintentos y marca temporal.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


class OutboxStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OutboxMessage:
    """Modelo in-memory/DB para persistencia transaccional de eventos de dominio."""

    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: str
    status: OutboxStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None

    @classmethod
    def create(
        cls,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: str,
    ) -> "OutboxMessage":
        return cls(
            id=uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )

    def mark_completed(self) -> None:
        self.status = OutboxStatus.COMPLETED
        self.processed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = OutboxStatus.FAILED
        self.retry_count += 1
        self.error_message = error


class OutboxDispatcher:
    """Worker asíncrono para despacho de eventos de Outbox."""

    def __init__(self) -> None:
        self._queue: List[OutboxMessage] = []

    def save(self, message: OutboxMessage) -> None:
        self._queue.append(message)

    async def dispatch_pending(self) -> int:
        pending = [m for m in self._queue if m.status == OutboxStatus.PENDING]
        for message in pending:
            try:
                # Simular o despachar evento a través de EventPublisherPort
                message.mark_completed()
            except Exception as exc:
                message.mark_failed(str(exc))
        return len(pending)
