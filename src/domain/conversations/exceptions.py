"""Domain exceptions for conversations."""

from src.domain.shared.exceptions import (
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
)


class ConversationNotFoundError(EntityNotFoundError):
    """Raised when a requested conversation aggregate is not found."""


class InvalidConversationTitleError(DomainValidationError):
    """Raised when a conversation title is empty or exceeds length limits."""


class ConsecutiveUserMessageError(DomainError):
    """Raised when attempting to append a user message before assistant responds."""


class ConsecutiveAssistantMessageError(DomainError):
    """Raised when attempting to append an assistant message without a preceding user message."""


class MessageValidationError(DomainValidationError):
    """Raised when a message payload violates domain invariants."""
