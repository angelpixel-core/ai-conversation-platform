"""Unified Domain Exceptions hierarchy for clean DDD error handling.

Rules:
- Zero external framework dependencies (standard library only).
- Consistent inheritance hierarchy rooted in DomainError (aliased as DomainException).
- Dual-inheritance with ValueError on validation exceptions for safe backward compatibility.
"""


class DomainError(Exception):
    """Base exception for all business-rule and domain invariant violations."""


# Semantic alias
DomainException = DomainError


class DomainValidationError(DomainError, ValueError):
    """Raised when an entity or value object fails structural domain invariants."""


class EntityNotFoundError(DomainError, ValueError):
    """Base exception raised when an aggregate root or entity is not found."""


class InvariantViolationError(DomainError, ValueError):
    """Raised when an operation would violate an aggregate consistency boundary."""
