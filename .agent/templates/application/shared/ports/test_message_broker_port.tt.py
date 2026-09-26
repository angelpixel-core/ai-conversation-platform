"""Template canónico para Pruebas Unitarias del Puerto MessageBrokerPort.

Reglas:
- Verifica que el puerto abstracto no pueda instanciarse directamente (ABC).
- Verifica que la implementación concreta satisfaga el contrato de publicación asíncrona.
- Usa @pytest.mark.anyio.
"""

from typing import Any
import pytest

from .message_broker_port.tt import MessageBrokerPort  # type: ignore[import-not-found]


def test_cannot_instantiate_abstract_message_broker_port() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        MessageBrokerPort()  # type: ignore[abstract]


@pytest.mark.anyio
async def test_concrete_message_broker_port_publish() -> None:
    class FakeMessageBroker(MessageBrokerPort):
        def __init__(self) -> None:
            self.published: list[tuple[str, Any]] = []

        async def publish(self, topic: str, envelope: Any) -> None:
            self.published.append((topic, envelope))

    broker = FakeMessageBroker()
    await broker.publish("test.topic", {"event": "data"})

    assert len(broker.published) == 1
    assert broker.published[0] == ("test.topic", {"event": "data"})
