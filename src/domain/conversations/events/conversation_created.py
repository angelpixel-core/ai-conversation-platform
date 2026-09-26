from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ConversationCreatedDomainEvent(DomainEvent):
    """Domain event emitted when a conversation is created."""

    conversation_id: UUID
