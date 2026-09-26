"""MSSQL Unit of Work adapter using SQLModel."""

from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlmodel import Session

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from src.infrastructure.persistence.mssql.outbox_repository import MssqlOutboxRepository
from src.infrastructure.persistence.mssql.repository import MssqlConversationRepository


class MssqlUnitOfWork(UnitOfWork):
    """Relational Unit of Work managing ACID transactions backed by SQLModel sessions."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._conversations: MssqlConversationRepository | None = None
        self._outbox: MssqlOutboxRepository | None = None

    @property
    def conversations(self) -> ConversationRepository:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Active repository for Conversation aggregate within this transaction."""
        if self._conversations is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._conversations

    @property
    def outbox(self) -> MssqlOutboxRepository:
        """Active repository for Outbox messages within this transaction."""
        if self._outbox is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._outbox

    def __enter__(self) -> Self:
        """Start a new database session and transaction."""
        self._session = self._session_factory()
        self._conversations = MssqlConversationRepository(session=self._session)
        self._outbox = MssqlOutboxRepository(session=self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the transaction context, rolling back if an exception occurred."""
        if self._session is not None:
            try:
                if exc_type is not None:
                    self.rollback()
            finally:
                self._session.close()
                self._session = None
                self._conversations = None
                self._outbox = None

    def commit(self) -> None:
        """Atomically commit all changes made within the active transaction."""
        if self._session is None:
            raise RuntimeError("Cannot commit: No active session.")
        self._session.commit()

    def rollback(self) -> None:
        """Roll back all pending uncommitted changes in the active transaction."""
        if self._session is None:
            raise RuntimeError("Cannot rollback: No active session.")
        self._session.rollback()
