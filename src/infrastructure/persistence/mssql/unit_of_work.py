"""MSSQL Unit of Work adapter using SQLModel."""

from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlmodel import Session

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.infrastructure.persistence.mssql.audit_repository import MssqlAuditRepository
from src.infrastructure.persistence.mssql.idempotency_repository import (
    MssqlIdempotencyRepository,
)
from src.infrastructure.persistence.mssql.mssql_knowledge_repository import (
    MssqlKnowledgeRepository,
)
from src.infrastructure.persistence.mssql.outbox_repository import MssqlOutboxRepository
from src.infrastructure.persistence.mssql.repository import MssqlConversationRepository
from src.infrastructure.persistence.mssql.stream_buffer_repository import (
    MssqlStreamBufferRepository,
)
from src.infrastructure.persistence.mssql.tenant_repository import MssqlTenantRepository


class MssqlUnitOfWork(UnitOfWork):
    """Relational Unit of Work managing ACID transactions backed by SQLModel sessions."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._conversations: MssqlConversationRepository | None = None
        self._outbox: MssqlOutboxRepository | None = None
        self._idempotency: MssqlIdempotencyRepository | None = None
        self._audit: MssqlAuditRepository | None = None
        self._stream_buffer: MssqlStreamBufferRepository | None = None
        self._tenants: MssqlTenantRepository | None = None
        self._knowledge: KnowledgeRepositoryPort | None = None

    @property
    def tenants(self) -> TenantRepositoryPort:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Active repository for Tenant aggregate within this transaction."""
        if self._tenants is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._tenants

    @property
    def conversations(self) -> ConversationRepository:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Active repository for Conversation aggregate within this transaction."""
        if self._conversations is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._conversations

    @property
    def knowledge(self) -> KnowledgeRepositoryPort:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Active repository for Knowledge documents within this transaction."""
        if self._knowledge is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._knowledge

    @property
    def outbox(self) -> MssqlOutboxRepository:
        """Active repository for Outbox messages within this transaction."""
        if self._outbox is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._outbox

    @property
    def idempotency(self) -> MssqlIdempotencyRepository:
        """Active repository for Idempotency records within this transaction."""
        if self._idempotency is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._idempotency

    @property
    def audit(self) -> MssqlAuditRepository:
        """Active repository for Audit logs within this transaction."""
        if self._audit is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._audit

    @property
    def stream_buffer(self) -> MssqlStreamBufferRepository:
        """Active repository for Stream buffer chunks within this transaction."""
        if self._stream_buffer is None:
            raise RuntimeError("UnitOfWork has not been started. Use 'with uow:' context.")
        return self._stream_buffer

    def __enter__(self) -> Self:
        """Start a new database session and transaction."""
        self._session = self._session_factory()
        self._conversations = MssqlConversationRepository(session=self._session)
        self._outbox = MssqlOutboxRepository(session=self._session)
        self._idempotency = MssqlIdempotencyRepository(session=self._session)
        self._audit = MssqlAuditRepository(session=self._session)
        self._stream_buffer = MssqlStreamBufferRepository(session=self._session)
        self._tenants = MssqlTenantRepository(session=self._session)
        self._knowledge = MssqlKnowledgeRepository(session=self._session)
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
                self._idempotency = None
                self._audit = None
                self._stream_buffer = None
                self._tenants = None
                self._knowledge = None

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
