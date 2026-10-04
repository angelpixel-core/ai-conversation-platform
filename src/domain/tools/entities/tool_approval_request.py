"""ToolApprovalRequest Aggregate Root."""

from datetime import UTC, datetime
from enum import StrEnum

from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.events.tool_events import (
    ToolApprovalRequiredDomainEvent,
    ToolApprovalResolvedDomainEvent,
)
from src.domain.tools.exceptions import InvalidApprovalStateError
from src.domain.tools.value_objects.tool_call import ToolCall


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ToolApprovalRequest(AggregateRoot):
    """Aggregate managing human-in-the-loop (HITL) approval lifecycle
    for critical tool executions.
    """

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
        if not approval_id or not approval_id.strip():
            raise ValueError("El approval_id no puede estar vacío.")
        if not conversation_id or not conversation_id.strip():
            raise ValueError("El conversation_id no puede estar vacío.")

        self._id = approval_id.strip()
        self._tenant_id = tenant_id
        self._conversation_id = conversation_id.strip()
        self._tool_call = tool_call
        self._status = status
        self._operator_id = operator_id
        self._justification = justification
        self._created_at = created_at or datetime.now(UTC)
        self._resolved_at = resolved_at

    @property
    def id(self) -> str:
        """Unique identifier of the approval request."""
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        """Tenant owning this approval request."""
        return self._tenant_id

    @property
    def conversation_id(self) -> str:
        """Conversation ID where the tool was requested."""
        return self._conversation_id

    @property
    def tool_call(self) -> ToolCall:
        """Tool call payload pending approval."""
        return self._tool_call

    @property
    def status(self) -> ApprovalStatus:
        """Current status of the approval request."""
        return self._status

    @property
    def operator_id(self) -> str | None:
        """Identifier of the human operator who resolved the request."""
        return self._operator_id

    @property
    def justification(self) -> str | None:
        """Operator notes or rejection justification."""
        return self._justification

    @property
    def created_at(self) -> datetime:
        """Timestamp of request creation."""
        return self._created_at

    @property
    def resolved_at(self) -> datetime | None:
        """Timestamp of resolution (approval/rejection), or None if pending."""
        return self._resolved_at

    @classmethod
    def create(
        cls,
        approval_id: str,
        tenant_id: TenantId,
        conversation_id: str,
        tool_call: ToolCall,
    ) -> "ToolApprovalRequest":
        """Factory method to initialize a new approval request and record the required event."""
        request = cls(
            approval_id=approval_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            tool_call=tool_call,
            status=ApprovalStatus.PENDING,
        )
        request.record_event(
            ToolApprovalRequiredDomainEvent(
                approval_id=request.id,
                tenant_id=str(request.tenant_id),
                conversation_id=request.conversation_id,
                tool_name=request.tool_call.tool_name,
                occurred_at=request.created_at,
            )
        )
        return request

    def approve(self, operator_id: str, justification: str | None = None) -> None:
        """Approves the tool execution request."""
        if self._status != ApprovalStatus.PENDING:
            raise InvalidApprovalStateError(
                f"No se puede aprobar una solicitud en estado '{self._status}'."
            )
        if not operator_id or not operator_id.strip():
            raise ValueError("El identificador del operador no puede estar vacío.")

        self._status = ApprovalStatus.APPROVED
        self._operator_id = operator_id.strip()
        self._justification = justification.strip() if justification else None
        self._resolved_at = datetime.now(UTC)

        self.record_event(
            ToolApprovalResolvedDomainEvent(
                approval_id=self._id,
                tenant_id=str(self._tenant_id),
                conversation_id=self._conversation_id,
                status=self._status.value,
                operator_id=self._operator_id,
                justification=self._justification,
                occurred_at=self._resolved_at,
            )
        )

    def reject(self, operator_id: str, reason: str | None = None) -> None:
        """Rejects the tool execution request."""
        if self._status != ApprovalStatus.PENDING:
            raise InvalidApprovalStateError(
                f"No se puede rechazar una solicitud en estado '{self._status}'."
            )
        if not operator_id or not operator_id.strip():
            raise ValueError("El identificador del operador no puede estar vacío.")

        self._status = ApprovalStatus.REJECTED
        self._operator_id = operator_id.strip()
        self._justification = reason.strip() if reason else None
        self._resolved_at = datetime.now(UTC)

        self.record_event(
            ToolApprovalResolvedDomainEvent(
                approval_id=self._id,
                tenant_id=str(self._tenant_id),
                conversation_id=self._conversation_id,
                status=self._status.value,
                operator_id=self._operator_id,
                justification=self._justification,
                occurred_at=self._resolved_at,
            )
        )
