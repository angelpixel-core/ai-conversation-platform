"""Domain exceptions for knowledge and document indexing."""

from src.domain.shared.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
)


class DocumentNotFoundError(EntityNotFoundError):
    """Raised when a requested knowledge document is not found."""


class DocumentValidationError(DomainValidationError):
    """Raised when document filename or metadata violates invariants."""


class InvalidDocumentChunkError(DomainValidationError):
    """Raised when document chunk indexing receives an invalid chunk count."""
