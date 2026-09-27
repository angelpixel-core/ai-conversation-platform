"""MessageBrokerPort secondary port for publishing event envelopes."""

from abc import ABC, abstractmethod

from src.domain.shared.events.event_envelope import EventEnvelope


class MessageBrokerPort(ABC):
    """Port for publishing structured event envelopes to a message broker."""

    @abstractmethod
    async def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Publish an event envelope to a designated topic or routing key.

        Args:
            topic: The destination exchange, topic, or queue routing key.
            envelope: Standardized integration event envelope.
        """
        raise NotImplementedError
