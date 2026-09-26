"""Domain exceptions for conversations."""

from src.domain.shared.domain_error import DomainError


class ConversationNotFoundError(DomainError):
    """Raised when a requested conversation aggregate is not found."""

    pass
