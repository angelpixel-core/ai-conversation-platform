"""Template canónico para el Adaptador en Memoria de Message Broker (InMemoryMessageBroker).

Reglas:
- Pertenece a src/infrastructure/messaging/in_memory/.
- Implementa MessageBrokerPort y EventConsumerPort.
- Emplea AnyIO para despacho asíncrono en memoria sin dependencias externas.
- Ideal para pruebas unitarias y de aplicación.
"""

from collections.abc import Awaitable, Callable
from typing import Any
import anyio

from src.application.shared.ports.event_consumer_port import EventConsumerPort
from src.application.shared.ports.message_broker_port import MessageBrokerPort


class InMemoryMessageBroker(MessageBrokerPort, EventConsumerPort):
    """Broker en memoria para pruebas y desarrollo local."""

    def __init__(self) -> None:
        self.published_messages: list[tuple[str, Any]] = []
        self._handlers: dict[str, list[Callable[[Any], Awaitable[None]]]] = {}
        self._is_consuming: bool = False

    def register_handler(
        self,
        topic: str,
        handler: Callable[[Any], Awaitable[None]],
    ) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, envelope: Any) -> None:
        self.published_messages.append((topic, envelope))
        if self._is_consuming and topic in self._handlers:
            for handler in self._handlers[topic]:
                await handler(envelope)

    async def start_consuming(self) -> None:
        self._is_consuming = True
        # Procesa mensajes acumulados previos si los hubiera
        for topic, envelope in self.published_messages:
            if topic in self._handlers:
                for handler in self._handlers[topic]:
                    await handler(envelope)

    async def stop_consuming(self) -> None:
        self._is_consuming = False
