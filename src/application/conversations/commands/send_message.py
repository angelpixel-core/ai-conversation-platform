"""Send message command and handler for user input ingestion."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.conversations.exceptions import ConversationNotFoundError


@dataclass(frozen=True)
class SendMessageCommand:
    """Command DTO representing an intent to append a user message."""

    conversation_id: UUID
    content: str


@dataclass(frozen=True)
class SendMessageResult:
    """Result DTO returned upon successful user message ingestion."""

    conversation_id: UUID
    role: str
    content: str
    created_at: datetime


class SendMessageCommandHandler:
    """Application use case for handling user message ingestion."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initializes the handler with a transactional unit of work.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, command: SendMessageCommand) -> SendMessageResult:
        """Appends a user message to a conversation aggregate.

        Args:
            command: SendMessageCommand payload.

        Returns:
            SendMessageResult with persisted message data.

        Raises:
            ConversationNotFoundError: If target conversation does not exist.
        """
        with self._unit_of_work as uow:
            conversation = uow.conversations.get(command.conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(
                    f"Conversation {command.conversation_id} not found."
                )

            message = conversation.append_user_message(command.content)
            uow.conversations.add(conversation)
            uow.commit()

            return SendMessageResult(
                conversation_id=conversation.id,
                role=message.role.value,
                content=message.content,
                created_at=message.created_at,
            )


__all__ = [
    "SendMessageCommand",
    "SendMessageCommandHandler",
    "SendMessageResult",
]
