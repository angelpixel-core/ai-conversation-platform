from abc import ABC
from typing import Any


class AggregateRoot(ABC):
    """
    Base class for all aggregate roots.
    It provides functionality to record and retrieve domain events.
    """

    def __init__(self) -> None:
        self._domain_events: list[Any] = []

    def record_event(self, event: Any) -> None:
        """Records a domain event."""
        self._domain_events.append(event)

    def pull_events(self) -> list[Any]:
        """Retrieves and clears all recorded domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
