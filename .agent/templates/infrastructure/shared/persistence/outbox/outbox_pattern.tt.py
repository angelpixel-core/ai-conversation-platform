"""Template canónico para el Patrón Transactional Outbox & Dispatcher Worker.

Reglas:
- Modelo de mensaje de Outbox registrado en la misma transacción que los agregados de dominio.
- Repositorio de Outbox desacoplado para almacenar y consultar mensajes.
- Dispatcher asíncrono que recibe el repositorio y EventPublisher inyectados por constructor.
- Marcado de eventos procesados o fallidos con registro de reintentos y marca temporal.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import inspect
from uuid import UUID, uuid4

from src.application.shared.ports.event_publisher import EventPublisher


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OutboxMessage:
    """Modelo para persistencia transaccional de eventos de dominio en Outbox."""

    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: str
    status: OutboxStatus
    created_at: datetime
    processed_at: datetime | None = None
    retry_count: int = 0
    error_message: str | None = None

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
            created_at=datetime.now(UTC),
        )

    def mark_completed(self) -> None:
        self.status = OutboxStatus.COMPLETED
        self.processed_at = datetime.now(UTC)

    def mark_failed(self, error: str) -> None:
        self.status = OutboxStatus.FAILED
        self.retry_count += 1
        self.error_message = error


class InMemoryOutboxRepository:
    """Adaptador de persistencia en memoria para mensajes de Outbox."""

    def __init__(self) -> None:
        self._messages: dict[UUID, OutboxMessage] = {}

    def save(self, message: OutboxMessage) -> None:
        self._messages[message.id] = message

    def get_by_id(self, message_id: UUID) -> OutboxMessage | None:
        return self._messages.get(message_id)

    def get_pending(self) -> list[OutboxMessage]:
        return [m for m in self._messages.values() if m.status == OutboxStatus.PENDING]

    def all(self) -> list[OutboxMessage]:
        return list(self._messages.values())


class OutboxDispatcher:
    """Worker asíncrono para despacho de eventos de Outbox."""

    def __init__(
        self,
        repository: InMemoryOutboxRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._repository = repository
        self._publisher = event_publisher

    async def dispatch_pending(self) -> int:
        pending = self._repository.get_pending()
        for message in pending:
            try:
                res = self._publisher.publish(message)
                if inspect.isawaitable(res):
                    await res
                message.mark_completed()
            except Exception as exc:
                message.mark_failed(str(exc))
            self._repository.save(message)
        return len(pending)
