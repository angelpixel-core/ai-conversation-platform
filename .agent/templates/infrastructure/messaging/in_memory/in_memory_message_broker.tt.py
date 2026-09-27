"""Template canónico para el Adaptador en Memoria de Message Broker (InMemoryMessageBroker).

Reglas:
- Pertenece a src/infrastructure/messaging/in_memory/.
- Implementa MessageBrokerPort y EventConsumerPort.
- Emplea estructuras en memoria para despacho asíncrono sin dependencias externas.
- Ideal para pruebas unitarias y de aplicación.
"""

from src.application.shared.ports.event_consumer_port import (
    EventConsumerPort,
    EventHandler,
)
from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope


class InMemoryMessageBroker(MessageBrokerPort, EventConsumerPort):
    """In-memory event broker for tests, simulations and fast local workflows."""

    def __init__(self) -> None:
        self.published_messages: list[tuple[str, EventEnvelope]] = []
        self._handlers: dict[str, list[EventHandler]] = {}
        self._is_consuming: bool = False
        self._dispatched_indices: set[int] = set()

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe an asynchronous handler to a designated topic."""
        self._handlers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Publish an event envelope to a topic."""
        idx = len(self.published_messages)
        self.published_messages.append((topic, envelope))

        if self._is_consuming and topic in self._handlers:
            self._dispatched_indices.add(idx)
            for handler in self._handlers[topic]:
                await handler(envelope)

    async def start_consuming(self) -> None:
        """Begin consuming events, flushing any previously buffered messages."""
        self._is_consuming = True

        for idx, (topic, envelope) in enumerate(self.published_messages):
            if idx not in self._dispatched_indices and topic in self._handlers:
                self._dispatched_indices.add(idx)
                for handler in self._handlers[topic]:
                    await handler(envelope)

    async def stop_consuming(self) -> None:
        """Stop consuming events."""
        self._is_consuming = False

    def clear(self) -> None:
        """Reset internal broker state."""
        self.published_messages.clear()
        self._handlers.clear()
        self._is_consuming = False
        self._dispatched_indices.clear()
