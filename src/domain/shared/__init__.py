"""Shared Domain Kernel package."""

from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.shared.domain_event import DomainEvent
from src.domain.shared.exceptions import (
    DomainError,
    DomainException,
    DomainValidationError,
    EntityNotFoundError,
    InvariantViolationError,
)

__all__ = [
    "AggregateRoot",
    "DomainError",
    "DomainEvent",
    "DomainException",
    "DomainValidationError",
    "EntityNotFoundError",
    "InvariantViolationError",
]
