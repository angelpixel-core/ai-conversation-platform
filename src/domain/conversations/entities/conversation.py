"""Conversation aggregate root and domain event emitters."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.domain.conversations.events.assistant_response_completed import (
    AssistantResponseCompletedDomainEvent,
)
from src.domain.conversations.events.conversation_created import ConversationCreatedDomainEvent
from src.domain.conversations.events.message_appended import MessageAppendedDomainEvent
from src.domain.conversations.exceptions import (
    ConsecutiveAssistantMessageError,
    ConsecutiveUserMessageError,
    InvalidConversationTitleError,
    MessageValidationError,
)
from src.domain.conversations.value_objects.message import Message, MessageRole
from src.domain.shared.aggregate_root import AggregateRoot


@dataclass(eq=False)
class Conversation(AggregateRoot):
    """Aggregate root managing conversation lifecycle and message sequence.

    Attributes:
        id: Unique aggregate identifier (UUIDv4).
        title: Normalized subject or title of the conversation.
        created_at: UTC timestamp when the conversation aggregate was initialized.
    """

    id: UUID
    title: str
    created_at: datetime
    tenant_id: str = "default-tenant"
    _messages: list[Message] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        super().__init__()

    @property
    def messages(self) -> tuple[Message, ...]:
        """Read-only access to conversation messages."""
        return tuple(self._messages)

    @property
    def can_append_user_message(self) -> bool:
        """Whether the conversation turn state allows appending a new user message."""
        return not self._messages or self._messages[-1].role != MessageRole.USER

    @classmethod
    def create(cls, title: str, tenant_id: str = "default-tenant") -> "Conversation":
        """Factory creating a new Conversation aggregate root.

        Args:
            title: Human-readable title or subject of the conversation.
            tenant_id: Owning tenant identifier for multi-tenant isolation.

        Returns:
            Newly created Conversation aggregate root.

        Raises:
            InvalidConversationTitleError: If title is empty or exceeds 200 characters.
        """
        normalized = title.strip()
        if not normalized:
            raise InvalidConversationTitleError("Conversation title cannot be empty.")
        if len(normalized) > 200:
            raise InvalidConversationTitleError("Conversation title cannot exceed 200 characters.")

        clean_tenant = tenant_id.strip() if tenant_id and tenant_id.strip() else "default-tenant"
        instance = cls(
            id=uuid4(),
            title=normalized,
            created_at=datetime.now(UTC),
            tenant_id=clean_tenant,
        )
        instance.record_event(ConversationCreatedDomainEvent(conversation_id=instance.id))
        return instance

    @classmethod
    def reconstitute(
        cls,
        conversation_id: UUID,
        title: str,
        created_at: datetime,
        messages: tuple[Message, ...] | list[Message] = (),
        tenant_id: str = "default-tenant",
    ) -> "Conversation":
        """Reconstitute aggregate from storage without emitting creation events.

        Args:
            conversation_id: Stored unique conversation identifier.
            title: Stored title of the conversation.
            created_at: Stored creation timestamp.
            messages: Existing messages belonging to the conversation.
            tenant_id: Stored tenant identifier owning the conversation.

        Returns:
            Reconstituted Conversation aggregate root.
        """
        clean_tenant = tenant_id.strip() if tenant_id and tenant_id.strip() else "default-tenant"
        instance = cls(
            id=conversation_id,
            title=title,
            created_at=created_at,
            tenant_id=clean_tenant,
        )
        instance._messages = list(messages)
        return instance

    def append_user_message(
        self,
        content: str,
        idempotency_key: str | None = None,
    ) -> Message:
        """Append a user message to the conversation.

        Args:
            content: Textual content provided by the human user.
            idempotency_key: Optional client-supplied idempotency key (UUIDv4).

        Returns:
            The newly created and appended Message value object.

        Raises:
            ConsecutiveUserMessageError: If the last message is already a user message.
            MessageValidationError: If message content violates length or formatting invariants.
        """
        if not self.can_append_user_message:
            raise ConsecutiveUserMessageError(
                "Cannot append user message before assistant responds."
            )

        try:
            msg = Message.create_user_message(content, idempotency_key=idempotency_key)
        except ValueError as exc:
            raise MessageValidationError(str(exc)) from exc

        if self._messages:
            min_next_time = self._messages[-1].created_at + timedelta(milliseconds=10)
            if msg.created_at < min_next_time:
                msg = Message(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    created_at=min_next_time,
                    idempotency_key=msg.idempotency_key,
                )

        self._messages.append(msg)
        self.record_event(MessageAppendedDomainEvent(conversation_id=self.id, message=msg))
        return msg

    def append_assistant_message(
        self,
        content: str,
        idempotency_key: str | None = None,
    ) -> Message:
        """Append an assistant response message to the conversation.

        Args:
            content: Textual response generated by the AI assistant.
            idempotency_key: Optional idempotency key correlated with the turn.

        Returns:
            The newly created and appended Message value object.

        Raises:
            ConsecutiveAssistantMessageError: If conversation is empty or last
                message was assistant.
            MessageValidationError: If content violates message length or formatting invariants.
        """
        if not self._messages or self._messages[-1].role != MessageRole.USER:
            raise ConsecutiveAssistantMessageError(
                "Cannot append assistant message without a preceding user message."
            )

        resolved_key = idempotency_key or self._messages[-1].idempotency_key

        try:
            msg = Message.create_assistant_message(content, idempotency_key=resolved_key)
        except ValueError as exc:
            raise MessageValidationError(str(exc)) from exc

        if self._messages:
            min_next_time = self._messages[-1].created_at + timedelta(milliseconds=10)
            if msg.created_at < min_next_time:
                msg = Message(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    created_at=min_next_time,
                    idempotency_key=msg.idempotency_key,
                )

        self._messages.append(msg)
        self.record_event(MessageAppendedDomainEvent(conversation_id=self.id, message=msg))
        self.record_event(
            AssistantResponseCompletedDomainEvent(conversation_id=self.id, message=msg)
        )
        return msg


__all__ = ["Conversation"]
