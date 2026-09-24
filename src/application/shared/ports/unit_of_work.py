from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from src.domain.conversations.ports.conversation_repository import ConversationRepository


class UnitOfWork(ABC):
    """Transaction boundary.

    A future PostgreSQL implementation can map this to one database
    transaction, committing repository changes and an outbox record together.
    """

    conversations: ConversationRepository

    @abstractmethod
    def __enter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
