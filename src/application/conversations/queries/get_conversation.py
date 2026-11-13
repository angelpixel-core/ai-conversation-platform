"""Query and handler for retrieving a conversation with full message history (RFC-33)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepositoryPort,
)


@dataclass(frozen=True)
class GetConversationQuery:
    """Query DTO requesting conversation state and message history by ID."""

    conversation_id: UUID
    tenant_id: str | None = None


@dataclass(frozen=True)
class ConversationMessageReadModel:
    """Read DTO representing an individual message in conversation history."""

    id: UUID
    role: str
    content: str
    created_at: datetime
    idempotency_key: str | None = None
    delivery_status: str = "DELIVERED"


@dataclass(frozen=True)
class GetConversationResult:
    """Read DTO returned by GetConversationQueryHandler."""

    conversation_id: UUID
    title: str
    tenant_id: str
    created_at: datetime
    can_append_user_message: bool
    messages: tuple[ConversationMessageReadModel, ...]


class GetConversationQueryHandler:
    """CQRS query handler for retrieving conversation history and turn status."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort | None = None,
        conversation_repository: ConversationRepositoryPort | None = None,
    ) -> None:
        """Initialize the query handler with a unit of work or conversation repository.

        Args:
            unit_of_work: Optional transactional unit of work providing conversation access.
            conversation_repository: Optional direct conversation read repository.

        Raises:
            ValueError: If neither unit_of_work nor conversation_repository is provided.
        """
        if unit_of_work is None and conversation_repository is None:
            raise ValueError("Either unit_of_work or conversation_repository must be provided.")
        self._unit_of_work = unit_of_work
        self._conversation_repository = conversation_repository

    def _load_conversation(self, conversation_id: UUID) -> Conversation | None:
        if self._unit_of_work is not None:
            with self._unit_of_work as uow:
                return uow.conversations.get(conversation_id)
        if self._conversation_repository is not None:
            return self._conversation_repository.get(conversation_id)
        return None

    def handle(self, query: GetConversationQuery) -> GetConversationResult:
        """Retrieve conversation history and turn availability isolated by tenant.

        Args:
            query: GetConversationQuery containing conversation_id and optional tenant_id.

        Returns:
            GetConversationResult with message list and can_append_user_message flag.

        Raises:
            ConversationNotFoundError: If conversation does not exist or belongs to another tenant.
        """
        conversation = self._load_conversation(query.conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {query.conversation_id} not found.")

        requested_tenant = query.tenant_id or get_current_tenant_id()
        if (
            requested_tenant
            and conversation.tenant_id != "default-tenant"
            and conversation.tenant_id != requested_tenant
        ):
            raise ConversationNotFoundError(f"Conversation {query.conversation_id} not found.")

        message_items = tuple(
            ConversationMessageReadModel(
                id=msg.id,
                role=msg.role.value,
                content=msg.content,
                created_at=msg.created_at,
                idempotency_key=msg.idempotency_key,
                delivery_status="DELIVERED",
            )
            for msg in conversation.messages
        )

        return GetConversationResult(
            conversation_id=conversation.id,
            title=conversation.title,
            tenant_id=conversation.tenant_id,
            created_at=conversation.created_at,
            can_append_user_message=conversation.can_append_user_message,
            messages=message_items,
        )


__all__ = [
    "ConversationMessageReadModel",
    "GetConversationQuery",
    "GetConversationQueryHandler",
    "GetConversationResult",
]

