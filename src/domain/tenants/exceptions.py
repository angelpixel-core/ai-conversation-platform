"""Domain exceptions for tenants, budgets, and policy quotas."""

from src.domain.shared.exceptions import (
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
)


class TenantNotFoundError(EntityNotFoundError):
    """Raised when a requested tenant organization does not exist."""


class TenantAlreadyExistsError(DomainError):
    """Raised when attempting to provision a tenant with an existing ID."""


class TenantSuspendedError(DomainError, ValueError):
    """Raised when attempting operational actions on a suspended tenant."""


class TenantValidationError(DomainValidationError):
    """Raised when tenant fields or attributes violate domain invariants."""


class InsufficientBudgetError(DomainError, ValueError):
    """Raised when available balance is insufficient to reserve or execute inference."""


class InvalidBudgetOperationError(DomainValidationError):
    """Raised when a budget arithmetic operation or top-up violates invariants."""


class ModelNotAllowedError(DomainError, ValueError):
    """Raised when an inference model is not authorized by the tenant policy."""
