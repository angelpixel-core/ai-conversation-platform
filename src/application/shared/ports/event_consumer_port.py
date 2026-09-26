"""EventConsumerPort secondary port for subscribing and consuming event envelopes."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from src.domain.shared.events.event_envelope import EventEnvelope

EventHandler = Callable[[EventEnvelope], Awaitable[None]]


class EventConsumerPort(ABC):
    """Port for subscribing handlers and orchestrating event consumption from a broker."""

    @abstractmethod
    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register an asynchronous handler for a designated topic.

        Args:
            topic: The source topic, queue, or routing key.
            handler: Asynchronous callback processing incoming event envelopes.
        """
        raise NotImplementedError

    @abstractmethod
    async def start_consuming(self) -> None:
        """Begin consuming messages from the broker queues."""
        raise NotImplementedError

    @abstractmethod
    async def stop_consuming(self) -> None:
        """Gracefully stop consuming messages and close channels."""
        raise NotImplementedError
