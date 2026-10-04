from abc import ABC, abstractmethod


class EventPublisherPort(ABC):
    """Port for publishing domain/application events."""

    @abstractmethod
    def publish(self, event: object) -> None:
        raise NotImplementedError


# Alias for backward compatibility
EventPublisher = EventPublisherPort
