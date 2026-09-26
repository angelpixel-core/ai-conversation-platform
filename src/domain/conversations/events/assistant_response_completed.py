"""AssistantResponseCompletedDomainEvent domain event."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.conversations.value_objects.message import Message


@dataclass(frozen=True)
class AssistantResponseCompletedDomainEvent:
    """Event emitted when an assistant AI streaming response completes."""

    conversation_id: UUID
    message: Message
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
