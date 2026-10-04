from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from src.domain.conversations.ports.conversation_repository import ConversationRepository
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)


class UnitOfWorkPort(ABC):
    """Transaction boundary interface (Unit of Work).

    Coordinates persistence operations and transaction boundaries across multiple
    domain aggregate repositories, ensuring atomic commits and outbox event dispatch.
    """

    conversations: ConversationRepository
    tenants: TenantRepositoryPort
    knowledge: KnowledgeRepositoryPort
    tool_approvals: ToolApprovalRepositoryPort

    @abstractmethod
    def __enter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError


# Alias for backward compatibility
UnitOfWork = UnitOfWorkPort
