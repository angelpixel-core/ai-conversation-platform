"""Base CQRS protocols and interfaces for commands and queries."""

from typing import Any, Protocol, TypeVar

TCommand = TypeVar("TCommand", contravariant=True)
TQuery = TypeVar("TQuery", contravariant=True)
TResult = TypeVar("TResult", covariant=True)


class CommandHandler(Protocol[TCommand, TResult]):
    """Protocol defining the execution contract for CQRS Command Handlers."""

    def handle(self, command: TCommand, *args: Any, **kwargs: Any) -> TResult:
        """Executes a command that mutates domain state."""
        ...


class AsyncCommandHandler(Protocol[TCommand, TResult]):
    """Protocol defining the asynchronous execution contract for CQRS Command Handlers."""

    async def handle(self, command: TCommand, *args: Any, **kwargs: Any) -> TResult:
        """Executes an asynchronous command that mutates domain state."""
        ...


class QueryHandler(Protocol[TQuery, TResult]):
    """Protocol defining the execution contract for CQRS Query Handlers."""

    def handle(self, query: TQuery, *args: Any, **kwargs: Any) -> TResult:
        """Executes a read-only query without producing side-effects."""
        ...


class AsyncQueryHandler(Protocol[TQuery, TResult]):
    """Protocol defining the asynchronous execution contract for CQRS Query Handlers."""

    async def handle(self, query: TQuery, *args: Any, **kwargs: Any) -> TResult:
        """Executes an asynchronous read-only query without producing side-effects."""
        ...
