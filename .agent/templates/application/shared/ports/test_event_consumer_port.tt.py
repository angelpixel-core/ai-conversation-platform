"""Template canónico para Pruebas Unitarias del Puerto EventConsumerPort.

Reglas:
- Verifica que el puerto abstracto no pueda instanciarse directamente (ABC).
- Verifica registro de handlers y ciclo de vida de consumo.
- Usa @pytest.mark.anyio.
"""

from collections.abc import Awaitable, Callable
from typing import Any
import pytest

from .event_consumer_port.tt import EventConsumerPort  # type: ignore[import-not-found]


def test_cannot_instantiate_abstract_event_consumer_port() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        EventConsumerPort()  # type: ignore[abstract]


@pytest.mark.anyio
async def test_concrete_event_consumer_lifecycle() -> None:
    class FakeConsumer(EventConsumerPort):
        def __init__(self) -> None:
            self.handlers: dict[str, list[Callable[[Any], Awaitable[None]]]] = {}
            self.is_consuming = False

        def register_handler(
            self,
            topic: str,
            handler: Callable[[Any], Awaitable[None]],
        ) -> None:
            self.handlers.setdefault(topic, []).append(handler)

        async def start_consuming(self) -> None:
            self.is_consuming = True

        async def stop_consuming(self) -> None:
            self.is_consuming = False

    consumer = FakeConsumer()
    received: list[Any] = []

    async def sample_handler(envelope: Any) -> None:
        received.append(envelope)

    consumer.register_handler("test.topic", sample_handler)
    assert "test.topic" in consumer.handlers

    await consumer.start_consuming()
    assert consumer.is_consuming is True

    await consumer.stop_consuming()
    assert consumer.is_consuming is False
