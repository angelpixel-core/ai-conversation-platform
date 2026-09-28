"""In-memory Tool Approval repository adapter for fast unit tests."""

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)


class InMemoryToolApprovalRepository(ToolApprovalRepositoryPort):
    """Fast in-memory dictionary-backed repository for tool approval requests."""

    def __init__(self) -> None:
        self._approvals: dict[tuple[str, str], ToolApprovalRequest] = {}

    def save(self, approval: ToolApprovalRequest) -> None:
        """Persists or updates an approval request."""
        self._approvals[(str(approval.tenant_id), approval.id)] = approval

    def get(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        """Retrieves an approval request by tenant and id."""
        return self._approvals.get((str(tenant_id), approval_id))

    def get_pending(self, tenant_id: TenantId) -> list[ToolApprovalRequest]:
        """Retrieves all pending approval requests for a tenant."""
        return [
            a
            for a in self._approvals.values()
            if a.tenant_id == tenant_id and a.status == ApprovalStatus.PENDING
        ]


# Alias for naming consistency across adapters
InMemoryToolApprovalRepositoryAdapter = InMemoryToolApprovalRepository
