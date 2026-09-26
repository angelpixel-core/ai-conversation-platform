"""Template canónico para Pruebas Unitarias de InMemoryMessageBroker.

Reglas:
- Verifica publicación en memoria.
- Verifica despacho hacia handlers registrados al consumir.
- Usa @pytest.mark.anyio.
"""

from typing import Any
import pytest

from .in_memory_message_broker.tt import InMemoryMessageBroker  # type: ignore[import-not-found]


@pytest.mark.anyio
async def test_in_memory_message_broker_publish_and_consume() -> None:
    broker = InMemoryMessageBroker()
    received: list[dict[str, Any]] = []

    async def sample_handler(envelope: dict[str, Any]) -> None:
        received.append(envelope)

    broker.register_handler("conversation.events", sample_handler)
    await broker.start_consuming()

    payload = {"event": "created", "id": 1}
    await broker.publish("conversation.events", payload)

    assert len(broker.published_messages) == 1
    assert len(received) == 1
    assert received[0] == payload

    await broker.stop_consuming()
