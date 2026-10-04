"""CQRS shared protocols and base types."""

from src.application.shared.cqrs.base import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)

__all__ = [
    "AsyncCommandHandler",
    "AsyncQueryHandler",
    "CommandHandler",
    "QueryHandler",
]
