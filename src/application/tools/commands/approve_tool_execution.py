"""Approve tool execution command and handler for Human-in-the-Loop workflows."""

from dataclasses import dataclass
from datetime import datetime

from src.application.shared.ports.event_publisher import EventPublisher
from src.domain.tenants.value_objects.tenant_id import TenantId
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


class ApproveToolExecutionHandler:
    """Handles operator approval for pending tool calls."""

    def __init__(
        self,
        tool_approval_repo: ToolApprovalRepositoryPort,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._repo = tool_approval_repo
        self._event_publisher = event_publisher

    def handle(self, command: ApproveToolExecutionCommand) -> ApproveToolExecutionResult:
        tenant_id = TenantId(command.tenant_id)
        approval = self._repo.get(tenant_id, command.approval_id)
        if approval is None:
            raise ValueError(f"Solicitud de aprobación '{command.approval_id}' no encontrada.")

        approval.approve(operator_id=command.operator_id, justification=command.justification)
        self._repo.save(approval)

        if self._event_publisher is not None:
            for event in approval.pull_events():
                self._event_publisher.publish(event)

        assert approval.operator_id is not None
        assert approval.resolved_at is not None

        return ApproveToolExecutionResult(
            approval_id=approval.id,
            status=approval.status.value,
            operator_id=approval.operator_id,
            justification=approval.justification,
            resolved_at=approval.resolved_at,
        )
