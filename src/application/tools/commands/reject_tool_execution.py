"""Reject tool execution command and handler for Human-in-the-Loop workflows."""

from dataclasses import dataclass
from datetime import datetime

from src.application.shared.ports.event_publisher import EventPublisherPort
from src.domain.shared.exceptions import InvariantViolationError
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.exceptions import ToolApprovalNotFoundError
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)


@dataclass(frozen=True)
class RejectToolExecutionCommand:
    """Command to reject a pending tool execution by an operator."""

    approval_id: str
    tenant_id: str
    operator_id: str
    reason: str | None = None


@dataclass(frozen=True)
class RejectToolExecutionResult:
    """Result returned after successfully rejecting a tool execution."""

    approval_id: str
    status: str
    operator_id: str
    reason: str | None
    resolved_at: datetime


class RejectToolExecutionCommandHandler:
    """Handles operator rejection for pending tool calls."""

    def __init__(
        self,
        tool_approval_repo: ToolApprovalRepositoryPort,
        event_publisher: EventPublisherPort | None = None,
    ) -> None:
        """Initializes the rejection command handler.

        Args:
            tool_approval_repo: Driven port for tool approval repository.
            event_publisher: Optional event publisher port for domain events.
        """
        self._repo = tool_approval_repo
        self._event_publisher = event_publisher

    def handle(self, command: RejectToolExecutionCommand) -> RejectToolExecutionResult:
        """Rejects a pending tool execution and dispatches rejection events.

        Args:
            command: RejectToolExecutionCommand payload.

        Returns:
            RejectToolExecutionResult with rejection metadata.

        Raises:
            ToolApprovalNotFoundError: If approval request does not exist.
        """
        tenant_id = TenantId(command.tenant_id)
        approval = self._repo.get(tenant_id, command.approval_id)
        if approval is None:
            raise ToolApprovalNotFoundError(
                f"Solicitud de aprobación '{command.approval_id}' no encontrada."
            )

        approval.reject(operator_id=command.operator_id, reason=command.reason)
        self._repo.save(approval)

        if self._event_publisher is not None:
            for event in approval.pull_events():
                self._event_publisher.publish(event)

        if approval.operator_id is None or approval.resolved_at is None:
            msg = "Tool approval resolution state is invalid"
            raise InvariantViolationError(msg)

        return RejectToolExecutionResult(
            approval_id=approval.id,
            status=approval.status.value,
            operator_id=approval.operator_id,
            reason=approval.justification,
            resolved_at=approval.resolved_at,
        )


__all__ = [
    "RejectToolExecutionCommand",
    "RejectToolExecutionCommandHandler",
    "RejectToolExecutionResult",
]
