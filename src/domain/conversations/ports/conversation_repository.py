from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.conversations.entities.conversation import Conversation


class ConversationRepositoryPort(ABC):
    """Persistence port owned by the domain/application boundary."""

    @abstractmethod
    def add(self, conversation: Conversation) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, conversation_id: UUID) -> Conversation | None:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[Conversation]:
        raise NotImplementedError


__all__ = ["ConversationRepositoryPort"]
