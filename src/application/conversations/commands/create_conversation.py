from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.domain.conversations.entities.conversation import Conversation


@dataclass(frozen=True)
class CreateConversationCommand:
    """Command DTO representing an intent to create a new conversation."""

    title: str
    tenant_id: str | None = None


@dataclass(frozen=True)
class CreateConversationResult:
    """Result DTO returned upon successful conversation creation."""

    conversation_id: UUID
    title: str
    tenant_id: str = "default-tenant"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "ACTIVE"


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
            CreateConversationResult with generated ID, title, tenant_id, created_at, and status.
        """
        resolved_tenant = command.tenant_id or get_current_tenant_id() or "default-tenant"
        with self._unit_of_work as uow:
            conversation = Conversation.create(command.title, tenant_id=resolved_tenant)
            uow.conversations.add(conversation)
            uow.commit()

            return CreateConversationResult(
                conversation_id=conversation.id,
                title=conversation.title,
                tenant_id=conversation.tenant_id,
                created_at=conversation.created_at,
                status="ACTIVE",
            )


__all__ = [
    "CreateConversationCommand",
    "CreateConversationCommandHandler",
    "CreateConversationResult",
]
