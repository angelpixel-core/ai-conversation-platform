"""Canonical test template: ToolApprovalRequest Aggregate Root."""

import pytest
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import ApprovalStatus, ToolApprovalRequest
from src.domain.tools.value_objects.tool_call import ToolCall


def test_tool_approval_request_lifecycle() -> None:
    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 100})
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-123",
        tool_call=call,
    )
    assert req.status == ApprovalStatus.PENDING

    req.approve(operator_id="op-1", justification="Verified with customer service")
    assert req.status == ApprovalStatus.APPROVED
    assert req.operator_id == "op-1"
    assert req.resolved_at is not None

    with pytest.raises(ValueError, match="estado"):
        req.reject(operator_id="op-2", reason="Too late")
