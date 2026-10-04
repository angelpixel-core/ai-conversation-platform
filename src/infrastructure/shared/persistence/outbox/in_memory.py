"""In-memory Transactional Outbox pattern implementation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class OutboxStatus(StrEnum):
    """Lifecycle status for an outbox message."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OutboxMessage:
    """Model for transactional persistence of domain events in Outbox."""

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

    def mark_published(self) -> None:
        self.status = OutboxStatus.PUBLISHED
        self.processed_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        self.status = OutboxStatus.COMPLETED
        self.processed_at = datetime.now(UTC)

    def mark_failed(self, error: str) -> None:
        self.status = OutboxStatus.FAILED
        self.retry_count += 1
        self.error_message = error


class InMemoryOutboxRepository:
    """In-memory repository adapter for Outbox messages."""

    def __init__(self) -> None:
        self._messages: dict[UUID, OutboxMessage] = {}

    def save(self, message: OutboxMessage) -> None:
        self._messages[message.id] = message

    def add(self, event: object) -> None:
        """Compatibility method for raw event appending."""
        if isinstance(event, OutboxMessage):
            self.save(event)
        else:
            msg = OutboxMessage.create(
                aggregate_type="DomainEvent",
                aggregate_id=uuid4(),
                event_type=type(event).__name__,
                payload=str(event),
            )
            self.save(msg)

    def get_by_id(self, message_id: UUID) -> OutboxMessage | None:
        return self._messages.get(message_id)

    def get_pending(self) -> list[OutboxMessage]:
        return [m for m in self._messages.values() if m.status == OutboxStatus.PENDING]

    def all(self) -> list[OutboxMessage]:
        return list(self._messages.values())


# Alias for backward compatibility
InMemoryOutbox = InMemoryOutboxRepository
InMemoryOutboxRepositoryAdapter = InMemoryOutboxRepository
