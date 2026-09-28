"""Unit tests for ToolApprovalRequest Aggregate Root and ApprovalStatus."""

from datetime import datetime

import pytest

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.events.tool_events import (
    ToolApprovalRequiredDomainEvent,
    ToolApprovalResolvedDomainEvent,
)
from src.domain.tools.value_objects.tool_call import ToolCall


def _sample_tool_call() -> ToolCall:
    return ToolCall(
        call_id="call-4912",
        tool_name="refund_order",
        arguments={"order_id": "ord-99", "amount": 150.0},
    )


def test_tool_approval_request_creation_default_pending() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-123",
        tool_call=call,
    )
    assert req.id == "appr-1"
    assert req.tenant_id == TenantId("corp-acme")
    assert req.conversation_id == "conv-123"
    assert req.tool_call == call
    assert req.status == ApprovalStatus.PENDING
    assert req.operator_id is None
    assert req.justification is None
    assert isinstance(req.created_at, datetime)
    assert req.resolved_at is None
    assert req.pull_events() == []


def test_tool_approval_request_factory_create_records_event() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest.create(
        approval_id="appr-2",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-456",
        tool_call=call,
    )
    assert req.status == ApprovalStatus.PENDING
    events = req.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, ToolApprovalRequiredDomainEvent)
    assert event.approval_id == "appr-2"
    assert event.tenant_id == "corp-acme"
    assert event.conversation_id == "conv-456"
    assert event.tool_name == "refund_order"


def test_tool_approval_request_invalid_id_raises_value_error() -> None:
    call = _sample_tool_call()
    with pytest.raises(ValueError, match="approval_id"):
        ToolApprovalRequest(
            approval_id="   ",
            tenant_id=TenantId("corp-acme"),
            conversation_id="conv-1",
            tool_call=call,
        )


def test_tool_approval_request_invalid_conversation_id_raises_value_error() -> None:
    call = _sample_tool_call()
    with pytest.raises(ValueError, match="conversation_id"):
        ToolApprovalRequest(
            approval_id="appr-1",
            tenant_id=TenantId("corp-acme"),
            conversation_id="",
            tool_call=call,
        )


def test_tool_approval_request_approve_success() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-1",
        tool_call=call,
    )
    req.approve(operator_id="operator-42", justification="Verified with customer care")

    assert req.status == ApprovalStatus.APPROVED
    assert req.operator_id == "operator-42"
    assert req.justification == "Verified with customer care"
    assert req.resolved_at is not None

    events = req.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, ToolApprovalResolvedDomainEvent)
    assert event.approval_id == "appr-1"
    assert event.tenant_id == "corp-acme"
    assert event.conversation_id == "conv-1"
    assert event.status == "APPROVED"
    assert event.operator_id == "operator-42"
    assert event.justification == "Verified with customer care"


def test_tool_approval_request_reject_success() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-1",
        tool_call=call,
    )
    req.reject(operator_id="operator-99", reason="Potential fraud attempt")

    assert req.status == ApprovalStatus.REJECTED
    assert req.operator_id == "operator-99"
    assert req.justification == "Potential fraud attempt"
    assert req.resolved_at is not None

    events = req.pull_events()
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, ToolApprovalResolvedDomainEvent)
    assert event.approval_id == "appr-1"
    assert event.status == "REJECTED"
    assert event.operator_id == "operator-99"
    assert event.justification == "Potential fraud attempt"


def test_tool_approval_request_empty_operator_id_raises_value_error() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-1",
        tool_call=call,
    )
    with pytest.raises(ValueError, match="operador"):
        req.approve(operator_id="   ")

    with pytest.raises(ValueError, match="operador"):
        req.reject(operator_id="")


def test_tool_approval_request_cannot_approve_twice() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-1",
        tool_call=call,
    )
    req.approve(operator_id="operator-1")
    with pytest.raises(ValueError, match="estado"):
        req.approve(operator_id="operator-2")


def test_tool_approval_request_cannot_reject_once_resolved() -> None:
    call = _sample_tool_call()
    req = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=TenantId("corp-acme"),
        conversation_id="conv-1",
        tool_call=call,
    )
    req.reject(operator_id="operator-1")
    with pytest.raises(ValueError, match="estado"):
        req.reject(operator_id="operator-2")
