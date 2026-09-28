"""Unit tests for ApproveToolExecutionCommandHandler."""

import pytest
from src.application.tools.commands.approve_tool_execution import (
    ApproveToolExecutionCommand,
    ApproveToolExecutionHandler,
)

from src.application.shared.ports.event_publisher import EventPublisher
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.events.tool_events import ToolApprovalResolvedDomainEvent
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)
from src.domain.tools.value_objects.tool_call import ToolCall


class FakeApprovalRepository(ToolApprovalRepositoryPort):
    def __init__(self) -> None:
        self.approvals: dict[tuple[str, str], ToolApprovalRequest] = {}

    def save(self, approval: ToolApprovalRequest) -> None:
        self.approvals[(str(approval.tenant_id), approval.id)] = approval

    def get(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        return self.approvals.get((str(tenant_id), approval_id))

    def get_pending(self, tenant_id: TenantId) -> list[ToolApprovalRequest]:
        return [
            a
            for a in self.approvals.values()
            if a.tenant_id == tenant_id and a.status == ApprovalStatus.PENDING
        ]


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


def test_approve_tool_execution_handler_success() -> None:
    repo = FakeApprovalRepository()
    publisher = FakeEventPublisher()
    handler = ApproveToolExecutionHandler(
        tool_approval_repo=repo,
        event_publisher=publisher,
    )

    tid = TenantId("corp-acme")
    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 100})
    approval = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call,
    )
    repo.save(approval)

    cmd = ApproveToolExecutionCommand(
        approval_id="appr-1",
        tenant_id="corp-acme",
        operator_id="operator-7",
        justification="Verified with manager",
    )
    result = handler.handle(cmd)

    assert result.approval_id == "appr-1"
    assert result.status == "APPROVED"
    assert result.operator_id == "operator-7"
    assert result.justification == "Verified with manager"
    assert result.resolved_at is not None

    stored = repo.get(tid, "appr-1")
    assert stored is not None
    assert stored.status == ApprovalStatus.APPROVED

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert isinstance(event, ToolApprovalResolvedDomainEvent)
    assert event.approval_id == "appr-1"
    assert event.status == "APPROVED"
    assert event.operator_id == "operator-7"


def test_approve_tool_execution_not_found_raises_value_error() -> None:
    repo = FakeApprovalRepository()
    handler = ApproveToolExecutionHandler(tool_approval_repo=repo)

    cmd = ApproveToolExecutionCommand(
        approval_id="missing",
        tenant_id="corp-acme",
        operator_id="operator-1",
    )
    with pytest.raises(ValueError, match="no encontrada"):
        handler.handle(cmd)


def test_approve_tool_execution_empty_operator_raises_value_error() -> None:
    repo = FakeApprovalRepository()
    handler = ApproveToolExecutionHandler(tool_approval_repo=repo)

    tid = TenantId("corp-acme")
    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 100})
    approval = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call,
    )
    repo.save(approval)

    cmd = ApproveToolExecutionCommand(
        approval_id="appr-1",
        tenant_id="corp-acme",
        operator_id="  ",
    )
    with pytest.raises(ValueError, match="operador"):
        handler.handle(cmd)
