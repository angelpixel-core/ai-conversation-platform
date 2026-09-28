from types import TracebackType
from typing import Self

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.infrastructure.persistence.in_memory.knowledge_repository import (
    InMemoryKnowledgeRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.repository import InMemoryConversationRepository
from src.infrastructure.persistence.in_memory.tenant_repository import (
    InMemoryTenantRepositoryAdapter,
)


class InMemoryUnitOfWork(UnitOfWork):
    """Transactional-looking local adapter.

    It is intentionally lightweight. The PostgreSQL implementation will
    provide the real ACID transaction boundary.
    """

    def __init__(self) -> None:
        self.conversations = InMemoryConversationRepository()
        self.tenants = InMemoryTenantRepositoryAdapter()
        self.knowledge = InMemoryKnowledgeRepositoryAdapter()
        self._committed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._committed = False
