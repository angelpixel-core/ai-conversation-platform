"""Unit tests for InMemoryToolApprovalRepository adapter."""

from src.infrastructure.persistence.in_memory.in_memory_tool_approval_repository import (
    InMemoryToolApprovalRepository,
)

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.value_objects.tool_call import ToolCall


def test_in_memory_tool_approval_repo_lifecycle() -> None:
    repo = InMemoryToolApprovalRepository()
    tid = TenantId("corp-acme")
    other_tid = TenantId("corp-other")

    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 80})
    appr = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call,
    )
    repo.save(appr)

    assert repo.get(tid, "appr-1") is not None
    assert repo.get(other_tid, "appr-1") is None

    pending = repo.get_pending(tid)
    assert len(pending) == 1

    appr.approve(operator_id="op-1", justification="Verified")
    repo.save(appr)

    assert repo.get(tid, "appr-1") is not None
    assert repo.get(tid, "appr-1").status == ApprovalStatus.APPROVED  # type: ignore[union-attr]
    assert len(repo.get_pending(tid)) == 0
