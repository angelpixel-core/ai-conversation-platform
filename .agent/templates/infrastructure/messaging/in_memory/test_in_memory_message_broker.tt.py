"""Template canónico para Pruebas Unitarias de InMemoryMessageBroker.

Reglas:
- Verifica publicación en memoria de EventEnvelope.
- Verifica despacho hacia handlers registrados al consumir.
- Verifica flush de mensajes bufferizados previos al start_consuming.
- Usa @pytest.mark.anyio.
"""

import pytest

from src.domain.shared.events.event_envelope import EventEnvelope
from .in_memory_message_broker.tt import InMemoryMessageBroker  # type: ignore[import-not-found]


@pytest.mark.anyio
async def test_in_memory_message_broker_publish_and_consume() -> None:
    broker = InMemoryMessageBroker()
    received: list[EventEnvelope] = []

    async def sample_handler(envelope: EventEnvelope) -> None:
        received.append(envelope)

    broker.subscribe("conversation.events", sample_handler)
    await broker.start_consuming()

    envelope = EventEnvelope.create(
        event_type="conversation.created",
        payload={"id": "conv-123"},
    )
    await broker.publish("conversation.events", envelope)

    assert len(broker.published_messages) == 1
    assert len(received) == 1
    assert received[0] == envelope

    await broker.stop_consuming()
