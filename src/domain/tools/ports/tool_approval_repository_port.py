"""Driven port contract for Tool Approval Request persistence."""

from abc import ABC, abstractmethod

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import ToolApprovalRequest


class ToolApprovalRepositoryPort(ABC):
    """Abstract repository for persisting and resolving tool approval requests
    with pessimistic locks.
    """

    @abstractmethod
    def save(self, approval: ToolApprovalRequest) -> None:
        """Persists or updates an approval request."""
        raise NotImplementedError

    @abstractmethod
    def get(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        """Retrieves an approval request by tenant and id."""
        raise NotImplementedError

    @abstractmethod
    def get_pending(self, tenant_id: TenantId) -> list[ToolApprovalRequest]:
        """Retrieves all pending approval requests for a tenant."""
        raise NotImplementedError
