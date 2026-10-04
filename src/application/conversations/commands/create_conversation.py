from dataclasses import dataclass
from uuid import UUID

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.conversations.entities.conversation import Conversation


@dataclass(frozen=True)
class CreateConversationCommand:
    """Command DTO representing an intent to create a new conversation."""

    title: str


@dataclass(frozen=True)
class CreateConversationResult:
    """Result DTO returned upon successful conversation creation."""

    conversation_id: UUID
    title: str


class CreateConversationCommandHandler:
    """Application use case for creating a new conversation."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initializes the handler with a transactional unit of work.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, command: CreateConversationCommand) -> CreateConversationResult:
        """Creates a conversation aggregate and commits the change.

        Args:
            command: Command payload containing the initial title.

        Returns:
            CreateConversationResult with generated ID and title.
        """
        with self._unit_of_work as uow:
            conversation = Conversation.create(command.title)
            uow.conversations.add(conversation)
            uow.commit()

            return CreateConversationResult(
                conversation_id=conversation.id,
                title=conversation.title,
            )


__all__ = [
    "CreateConversationCommand",
    "CreateConversationCommandHandler",
    "CreateConversationResult",
]
