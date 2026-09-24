from abc import ABC, abstractmethod


class EventPublisher(ABC):
    """Port for publishing domain/application events."""

    @abstractmethod
    def publish(self, event: object) -> None:
        raise NotImplementedError
