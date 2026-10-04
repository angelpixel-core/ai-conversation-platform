"""Append assistant message command and handler for stream closure."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.conversations.exceptions import ConversationNotFoundError


@dataclass(frozen=True)
class AppendAssistantMessageCommand:
    """Command DTO representing an intent to append an assistant response message."""

    conversation_id: UUID
    content: str


@dataclass(frozen=True)
class AppendAssistantMessageResult:
    """Result DTO returned upon successful assistant message persistence."""

    conversation_id: UUID
    role: str
    content: str
    created_at: datetime


class AppendAssistantMessageCommandHandler:
    """Application use case for appending completed assistant responses."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initializes the handler with a transactional unit of work.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, command: AppendAssistantMessageCommand) -> AppendAssistantMessageResult:
        """Appends an assistant message to a conversation aggregate.

        Args:
            command: AppendAssistantMessageCommand payload.

        Returns:
            AppendAssistantMessageResult with persisted message data.

        Raises:
            ConversationNotFoundError: If target conversation does not exist.
        """
        with self._unit_of_work as uow:
            conversation = uow.conversations.get(command.conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(
                    f"Conversation {command.conversation_id} not found."
                )

            message = conversation.append_assistant_message(command.content)
            uow.conversations.add(conversation)
            uow.commit()

            return AppendAssistantMessageResult(
                conversation_id=conversation.id,
                role=message.role.value,
                content=message.content,
                created_at=message.created_at,
            )


# Alias for backward compatibility
AppendAssistantMessageHandler = AppendAssistantMessageCommandHandler
