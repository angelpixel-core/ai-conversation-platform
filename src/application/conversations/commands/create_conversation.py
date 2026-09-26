from dataclasses import dataclass
from uuid import UUID

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.conversations.entities.conversation import Conversation


@dataclass(frozen=True)
class CreateConversationCommand:
    title: str


@dataclass(frozen=True)
class CreateConversationResult:
    conversation_id: UUID
    title: str


class CreateConversationHandler:
    """Application use case for creating a conversation."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def handle(self, command: CreateConversationCommand) -> CreateConversationResult:
        with self._unit_of_work as uow:
            conversation = Conversation.create(command.title)
            uow.conversations.add(conversation)
            uow.commit()

            return CreateConversationResult(
                conversation_id=conversation.id,
                title=conversation.title,
            )
