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
    """Lifecycle status of a tool approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ToolApprovalRequest(AggregateRoot):
    """Aggregate managing human-in-the-loop (HITL) approval lifecycle.

    Guards high-risk or sensitive tool executions requiring human authorization.
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
        """Initialize a ToolApprovalRequest aggregate.

        Args:
            approval_id: Unique string identifier for the approval request.
            tenant_id: TenantId owning the conversation and tool request.
            conversation_id: Identifier of the conversation triggering the tool.
            tool_call: Immutable ToolCall payload containing tool name and arguments.
            status: Operational status. Defaults to PENDING.
            operator_id: Optional identifier of the resolving operator.
            justification: Optional explanation or audit notes.
            created_at: Optional UTC creation timestamp. Defaults to now.
            resolved_at: Optional UTC resolution timestamp.

        Raises:
            ValueError: If approval_id or conversation_id is empty or whitespace.
        """
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
        """str: Unique identifier of the approval request."""
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        """TenantId: Tenant owning this approval request."""
        return self._tenant_id

    @property
    def conversation_id(self) -> str:
        """str: Conversation ID where the tool was requested."""
        return self._conversation_id

    @property
    def tool_call(self) -> ToolCall:
        """ToolCall: Tool call payload pending approval."""
        return self._tool_call

    @property
    def status(self) -> ApprovalStatus:
        """ApprovalStatus: Current status of the approval request."""
        return self._status

    @property
    def operator_id(self) -> str | None:
        """str | None: Identifier of the operator who resolved the request."""
        return self._operator_id

    @property
    def justification(self) -> str | None:
        """str | None: Operator notes or rejection justification."""
        return self._justification

    @property
    def created_at(self) -> datetime:
        """datetime: Timestamp of request creation."""
        return self._created_at

    @property
    def resolved_at(self) -> datetime | None:
        """datetime | None: Timestamp of resolution, or None if pending."""
        return self._resolved_at

    @classmethod
    def create(
        cls,
        approval_id: str,
        tenant_id: TenantId,
        conversation_id: str,
        tool_call: ToolCall,
    ) -> "ToolApprovalRequest":
        """Factory initializing a new approval request and recording approval required event.

        Args:
            approval_id: Unique string identifier for the request.
            tenant_id: TenantId scoping ownership.
            conversation_id: Conversation originating the tool call.
            tool_call: ToolCall value object containing parameters.

        Returns:
            Newly created ToolApprovalRequest aggregate in PENDING status.
        """
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
        """Approve the tool execution request.

        Args:
            operator_id: Identifier of the authorizing operator.
            justification: Optional justification or audit explanation.

        Raises:
            InvalidApprovalStateError: If current status is not PENDING.
            ValueError: If operator_id is empty or whitespace.
        """
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
        """Reject the tool execution request.

        Args:
            operator_id: Identifier of the rejecting operator.
            reason: Optional justification or rejection explanation.

        Raises:
            InvalidApprovalStateError: If current status is not PENDING.
            ValueError: If operator_id is empty or whitespace.
        """
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


__all__ = ["ApprovalStatus", "ToolApprovalRequest"]
