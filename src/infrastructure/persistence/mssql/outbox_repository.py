"""MSSQL Transactional Outbox Repository adapter using SQLModel."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Session, select

from src.infrastructure.persistence.mssql.models import OutboxMessageModel
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage, OutboxStatus


class MssqlOutboxRepositoryAdapter:
    """Relational adapter for transactional persistence of domain events in the outbox."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, message: OutboxMessage) -> None:
        """Persist or update an outbox message inside the active database session."""
        existing = self._session.get(OutboxMessageModel, message.id)
        if existing is not None:
            existing.status = message.status.value
            existing.processed_at = message.processed_at
            existing.error_message = message.error_message
            self._session.add(existing)
        else:
            model = OutboxMessageModel(
                id=message.id,
                event_type=message.event_type,
                payload=message.payload,
                status=message.status.value,
                created_at=message.created_at,
                processed_at=message.processed_at,
                error_message=message.error_message,
            )
            self._session.add(model)

    def add(self, event: object) -> None:
        """Append an event or OutboxMessage to the outbox."""
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
        """Retrieve an outbox message by its primary identifier."""
        model = self._session.get(OutboxMessageModel, message_id)
        if model is None:
            return None
        return self._to_outbox_message(model)

    def get_pending(self, limit: int = 100) -> list[OutboxMessage]:
        """Fetch pending outbox messages ordered chronologically."""
        statement = (
            select(OutboxMessageModel)
            .where(OutboxMessageModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxMessageModel.created_at, OutboxMessageModel.id)  # type: ignore[arg-type]
            .limit(limit)
        )
        results = self._session.exec(statement).all()
        return [self._to_outbox_message(m) for m in results]

    def mark_as_published(self, message_id: UUID) -> None:
        """Mark an outbox message as successfully published to the event broker."""
        model = self._session.get(OutboxMessageModel, message_id)
        if model is not None:
            model.status = OutboxStatus.PUBLISHED.value
            model.processed_at = datetime.now(UTC)
            self._session.add(model)

    def mark_as_dispatched(self, message_id: UUID) -> None:
        """Mark an outbox message as successfully dispatched."""
        model = self._session.get(OutboxMessageModel, message_id)
        if model is not None:
            model.status = OutboxStatus.COMPLETED.value
            model.processed_at = datetime.now(UTC)
            self._session.add(model)

    def mark_as_completed(self, message_id: UUID) -> None:
        """Alias for mark_as_dispatched."""
        self.mark_as_dispatched(message_id)

    def mark_as_failed(self, message_id: UUID, error: str) -> None:
        """Mark an outbox message as failed with an error message."""
        model = self._session.get(OutboxMessageModel, message_id)
        if model is not None:
            model.status = OutboxStatus.FAILED.value
            model.error_message = error
            self._session.add(model)

    @staticmethod
    def _to_outbox_message(model: OutboxMessageModel) -> OutboxMessage:
        return OutboxMessage(
            id=model.id,
            aggregate_type="Conversation",
            aggregate_id=model.id,
            event_type=model.event_type,
            payload=model.payload,
            status=OutboxStatus(model.status),
            created_at=model.created_at,
            processed_at=model.processed_at,
            error_message=model.error_message,
        )


__all__ = ["MssqlOutboxRepositoryAdapter"]
