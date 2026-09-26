from uuid import UUID

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.ports.conversation_repository import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    """Simple adapter used for the first local vertical slice."""

    def __init__(self) -> None:
        self._items: dict[UUID, Conversation] = {}

    def add(self, conversation: Conversation) -> None:
        self._items[conversation.id] = conversation

    def get(self, conversation_id: UUID) -> Conversation | None:
        return self._items.get(conversation_id)

    def list(self) -> list[Conversation]:
        return list(self._items.values())
