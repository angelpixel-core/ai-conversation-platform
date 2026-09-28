"""Canonical test template: ToolApprovalRepositoryPort Driven Port."""

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import ToolApprovalRequest
from src.domain.tools.ports.tool_approval_repository_port import ToolApprovalRepositoryPort
from src.domain.tools.value_objects.tool_call import ToolCall


class FakeToolApprovalRepository(ToolApprovalRepositoryPort):
    def __init__(self) -> None:
        self.approvals: dict[tuple[str, str], ToolApprovalRequest] = {}

    def save(self, approval: ToolApprovalRequest) -> None:
        self.approvals[(str(approval.tenant_id), approval.id)] = approval

    def get(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        return self.approvals.get((str(tenant_id), approval_id))

    def get_pending(self, tenant_id: TenantId) -> list[ToolApprovalRequest]:
        return [
            a for a in self.approvals.values()
            if a.tenant_id == tenant_id and a.status.value == "PENDING"
        ]


def test_tool_approval_repository_contract() -> None:
    repo: ToolApprovalRepositoryPort = FakeToolApprovalRepository()
    tid = TenantId("corp-acme")
    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 50})
    appr = ToolApprovalRequest(approval_id="appr-1", tenant_id=tid, conversation_id="conv-1", tool_call=call)

    repo.save(appr)
    fetched = repo.get(tid, "appr-1")
    assert fetched is not None
    assert fetched.tool_call.tool_name == "refund_order"

    pending = repo.get_pending(tid)
    assert len(pending) == 1
