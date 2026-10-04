from abc import ABC, abstractmethod


class EventPublisherPort(ABC):
    """Port for publishing domain/application events."""

    @abstractmethod
    def publish(self, event: object) -> None:
        raise NotImplementedError


__all__ = ["EventPublisherPort"]
