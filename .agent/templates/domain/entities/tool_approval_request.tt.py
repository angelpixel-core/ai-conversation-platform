"""Canonical template: ToolApprovalRequest Aggregate Root."""

from datetime import UTC, datetime
from enum import StrEnum

from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.value_objects.tool_call import ToolCall


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ToolApprovalRequest(AggregateRoot):
    """Aggregate managing human-in-the-loop (HITL) approval lifecycle for critical tool executions."""

    def __init__(
        self,
        approval_id: str,
        tenant_id: TenantId,
        conversation_id: str,
        tool_call: ToolCall,
        status: ApprovalStatus = ApprovalStatus.PENDING,
        operator_id: str | None = None,
        justification: str | None = None,
        created_at: datetime | None = None,
        resolved_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = approval_id
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.tool_call = tool_call
        self.status = status
        self.operator_id = operator_id
        self.justification = justification
        self.created_at = created_at or datetime.now(UTC)
        self.resolved_at = resolved_at

    def approve(self, operator_id: str, justification: str | None = None) -> None:
        """Approves the tool execution request."""
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"No se puede aprobar una solicitud en estado '{self.status}'.")
        if not operator_id.strip():
            raise ValueError("El identificador del operador no puede estar vacío.")

        self.status = ApprovalStatus.APPROVED
        self.operator_id = operator_id.strip()
        self.justification = justification.strip() if justification else None
        self.resolved_at = datetime.now(UTC)

    def reject(self, operator_id: str, reason: str | None = None) -> None:
        """Rejects the tool execution request."""
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"No se puede rechazar una solicitud en estado '{self.status}'.")
        if not operator_id.strip():
            raise ValueError("El identificador del operador no puede estar vacío.")

        self.status = ApprovalStatus.REJECTED
        self.operator_id = operator_id.strip()
        self.justification = reason.strip() if reason else None
        self.resolved_at = datetime.now(UTC)
