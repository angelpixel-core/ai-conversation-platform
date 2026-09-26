"""
Template canónico para Pruebas de Integración del Patrón Transactional Outbox.
Reglas:
- Verifica la adición atómica de mensajes de Outbox, despacho asíncrono y cambios de estado (PENDING -> COMPLETED / FAILED).
"""

from uuid import uuid4
import pytest

from .outbox_pattern import OutboxMessage, OutboxStatus, OutboxDispatcher


@pytest.mark.asyncio
async def test_outbox_dispatcher_processes_pending_messages() -> None:
    # Arrange
    dispatcher = OutboxDispatcher()
    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppendedDomainEvent",
        payload='{"role": "user", "content": "Hola"}',
    )
    dispatcher.save(msg)

    # Act
    processed_count = await dispatcher.dispatch_pending()

    # Assert
    assert processed_count == 1
    assert msg.status == OutboxStatus.COMPLETED
    assert msg.processed_at is not None
