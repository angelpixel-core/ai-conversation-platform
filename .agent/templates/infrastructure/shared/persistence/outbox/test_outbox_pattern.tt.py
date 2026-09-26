"""Template canónico para Pruebas de Integración del Patrón Transactional Outbox.

Reglas:
- Verifica la adición atómica de mensajes de Outbox, despacho asíncrono y cambios de estado.
- Usa @pytest.mark.anyio para compatibilidad con el entorno de pruebas asíncronas.
"""

from uuid import uuid4

import pytest

from src.application.shared.ports.event_publisher import EventPublisher
from .outbox_pattern import (
    InMemoryOutboxRepository,
    OutboxDispatcher,
    OutboxMessage,
    OutboxStatus,
)


class DummyEventPublisher(EventPublisher):
    def __init__(self, should_fail: bool = False) -> None:
        self.published_events: list[object] = []
        self.should_fail = should_fail

    def publish(self, event: object) -> None:
        if self.should_fail:
            raise RuntimeError("Error de conexión con broker de eventos")
        self.published_events.append(event)


@pytest.mark.anyio
async def test_outbox_dispatcher_processes_pending_messages() -> None:
    # Arrange
    repository = InMemoryOutboxRepository()
    publisher = DummyEventPublisher()
    dispatcher = OutboxDispatcher(repository=repository, event_publisher=publisher)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppendedDomainEvent",
        payload='{"role": "user", "content": "Hola"}',
    )
    repository.save(msg)

    # Act
    processed_count = await dispatcher.dispatch_pending()

    # Assert
    assert processed_count == 1
    assert msg.status == OutboxStatus.COMPLETED
    assert msg.processed_at is not None
    assert len(publisher.published_events) == 1


@pytest.mark.anyio
async def test_outbox_dispatcher_marks_failed_on_publisher_error() -> None:
    # Arrange
    repository = InMemoryOutboxRepository()
    failing_publisher = DummyEventPublisher(should_fail=True)
    dispatcher = OutboxDispatcher(repository=repository, event_publisher=failing_publisher)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppendedDomainEvent",
        payload='{"role": "user", "content": "Hola"}',
    )
    repository.save(msg)

    # Act
    processed_count = await dispatcher.dispatch_pending()

    # Assert
    assert processed_count == 1
    assert msg.status == OutboxStatus.FAILED
    assert msg.retry_count == 1
    assert msg.error_message == "Error de conexión con broker de eventos"
