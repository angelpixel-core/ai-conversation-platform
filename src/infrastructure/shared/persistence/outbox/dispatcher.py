"""Outbox dispatcher worker for asynchronous event delivery."""

import inspect
from typing import Any

from src.application.shared.ports.event_publisher import EventPublisherPort
from src.infrastructure.shared.persistence.outbox.in_memory import (
    InMemoryOutboxRepositoryAdapter,
)


class OutboxDispatcherAdapter:
    """Asynchronous worker for dispatching pending outbox messages."""

    def __init__(
        self,
        repository: InMemoryOutboxRepositoryAdapter,
        event_publisher: EventPublisherPort,
    ) -> None:
        self._repository = repository
        self._publisher = event_publisher

    async def dispatch_pending(self) -> int:
        """Process all pending outbox messages and publish them via EventPublisherPort.

        Returns:
            int: Number of pending messages processed.
        """
        pending = self._repository.get_pending()
        for message in pending:
            try:
                res: Any = self._publisher.publish(message)
                if inspect.isawaitable(res):
                    await res
                message.mark_completed()
            except Exception as exc:
                message.mark_failed(str(exc))

            self._repository.save(message)

        return len(pending)


__all__ = ["OutboxDispatcherAdapter"]
