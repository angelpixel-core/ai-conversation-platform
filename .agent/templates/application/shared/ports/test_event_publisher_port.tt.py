"""Template canónico para Pruebas Unitarias del Puerto de Publicación de Eventos (Application Port).

Reglas:
- Verifica que el puerto abstracto no pueda instanciarse directamente (ABC).
- Verifica que una implementación concreta satisfaga la firma asíncrona de publicación.
- Usa @pytest.mark.anyio.
"""

from typing import Any
import pytest

from .event_publisher_port.tt import EventPublisherPort  # type: ignore[import-not-found]


def test_cannot_instantiate_abstract_event_publisher_port() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        EventPublisherPort()  # type: ignore[abstract]


@pytest.mark.anyio
async def test_concrete_event_publisher_implementation() -> None:
    class InMemoryEventPublisher(EventPublisherPort):
        def __init__(self) -> None:
            self.published_events: list[Any] = []

        async def publish(self, event: Any) -> None:
            self.published_events.append(event)

    publisher = InMemoryEventPublisher()
    test_event = {"event_type": "item_created", "id": 123}

    await publisher.publish(test_event)

    assert len(publisher.published_events) == 1
    assert publisher.published_events[0] == test_event
