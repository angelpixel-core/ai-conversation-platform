"""Approve tool execution command and handler for Human-in-the-Loop workflows."""

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
class ApproveToolExecutionCommand:
    """Command to approve a pending tool execution by an operator."""

    approval_id: str
    tenant_id: str
    operator_id: str
    justification: str | None = None


@dataclass(frozen=True)
class ApproveToolExecutionResult:
    """Result returned after successfully approving a tool execution."""

    approval_id: str
    status: str
    operator_id: str
    justification: str | None
    resolved_at: datetime


class ApproveToolExecutionCommandHandler:
    """Handles operator approval for pending tool calls."""

    def __init__(
        self,
        tool_approval_repo: ToolApprovalRepositoryPort,
        event_publisher: EventPublisherPort | None = None,
    ) -> None:
        """Initializes the approval command handler.

        Args:
            tool_approval_repo: Driven port for tool approval repository.
            event_publisher: Optional event publisher port for domain events.
        """
        self._repo = tool_approval_repo
        self._event_publisher = event_publisher

    def handle(self, command: ApproveToolExecutionCommand) -> ApproveToolExecutionResult:
        """Approves a pending tool execution and dispatches approval events.

        Args:
            command: ApproveToolExecutionCommand payload.

        Returns:
            ApproveToolExecutionResult with resolution status.

        Raises:
            ToolApprovalNotFoundError: If approval request does not exist.
        """
        tenant_id = TenantId(command.tenant_id)
        approval = self._repo.get(tenant_id, command.approval_id)
        if approval is None:
            raise ToolApprovalNotFoundError(
                f"Solicitud de aprobación '{command.approval_id}' no encontrada."
            )

        approval.approve(operator_id=command.operator_id, justification=command.justification)
        self._repo.save(approval)

        if self._event_publisher is not None:
            for event in approval.pull_events():
                self._event_publisher.publish(event)

        if approval.operator_id is None or approval.resolved_at is None:
            msg = "Tool approval resolution state is invalid"
            raise InvariantViolationError(msg)

        return ApproveToolExecutionResult(
            approval_id=approval.id,
            status=approval.status.value,
            operator_id=approval.operator_id,
            justification=approval.justification,
            resolved_at=approval.resolved_at,
        )


# Alias for backward compatibility
ApproveToolExecutionHandler = ApproveToolExecutionCommandHandler
