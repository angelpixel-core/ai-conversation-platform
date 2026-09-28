"""Domain exceptions for knowledge and document indexing."""

from src.domain.shared.domain_error import DomainError


class DocumentNotFoundError(DomainError):
    """Raised when a requested knowledge document is not found."""

    pass
