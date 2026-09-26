"""Template canónico para Adaptador Unit of Work Relacional con SQLModel.

Reglas:
- Implementa el puerto abstracto UnitOfWork de la capa de Aplicación.
- Maneja el ciclo de vida de la transacción (begin, commit, rollback) a través del context manager.
- Expone los repositorios de conversaciones y outbox bajo la misma sesión/transacción atómica.
"""

from collections.abc import Callable
from types import TracebackType
from sqlmodel import Session

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from .outbox_repository import SqlModelOutboxRepository
from .repository import SqlModelConversationRepository


class SqlModelUnitOfWork(UnitOfWork):
    """Adaptador de Unit of Work relacional respaldado por sesiones de SQLModel."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._conversations: SqlModelConversationRepository | None = None
        self._outbox: SqlModelOutboxRepository | None = None

    @property
    def conversations(self) -> ConversationRepository:
        if self._conversations is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._conversations

    @property
    def outbox(self) -> SqlModelOutboxRepository:
        if self._outbox is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._outbox

    def __enter__(self) -> "SqlModelUnitOfWork":
        self._session = self._session_factory()
        self._conversations = SqlModelConversationRepository(session=self._session)
        self._outbox = SqlModelOutboxRepository(session=self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
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
        if self._session is None:
            raise RuntimeError("Cannot commit: No active session.")
        self._session.commit()

    def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Cannot rollback: No active session.")
        self._session.rollback()
