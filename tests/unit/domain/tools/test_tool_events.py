"""Unit tests for Tool Domain Events."""

from datetime import UTC, datetime

import pytest
from src.domain.tools.events.tool_events import (
    ToolApprovalRequiredDomainEvent,
    ToolApprovalResolvedDomainEvent,
    ToolCallRequestedDomainEvent,
    ToolExecutionCompletedDomainEvent,
)


def test_tool_call_requested_domain_event() -> None:
    now = datetime.now(UTC)
    event = ToolCallRequestedDomainEvent(
        call_id="call-1",
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_name="refund_order",
        arguments={"amount": 100},
        occurred_at=now,
    )
    assert event.call_id == "call-1"
    assert event.tenant_id == "corp-acme"
    assert event.conversation_id == "conv-1"
    assert event.tool_name == "refund_order"
    assert event.arguments == {"amount": 100}
    assert event.occurred_at == now

    with pytest.raises(AttributeError):
        event.tool_name = "modified"  # type: ignore[misc]


def test_tool_approval_required_domain_event() -> None:
    now = datetime.now(UTC)
    event = ToolApprovalRequiredDomainEvent(
        approval_id="appr-1",
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_name="delete_account",
        occurred_at=now,
    )
    assert event.approval_id == "appr-1"
    assert event.tenant_id == "corp-acme"
    assert event.conversation_id == "conv-1"
    assert event.tool_name == "delete_account"
    assert event.occurred_at == now

    with pytest.raises(AttributeError):
        event.approval_id = "modified"  # type: ignore[misc]


def test_tool_execution_completed_domain_event() -> None:
    now = datetime.now(UTC)
    event = ToolExecutionCompletedDomainEvent(
        call_id="call-1",
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_name="weather_check",
        is_error=False,
        execution_time_ms=15.4,
        occurred_at=now,
    )
    assert event.call_id == "call-1"
    assert event.tenant_id == "corp-acme"
    assert event.conversation_id == "conv-1"
    assert event.tool_name == "weather_check"
    assert event.is_error is False
    assert event.execution_time_ms == 15.4
    assert event.occurred_at == now

    with pytest.raises(AttributeError):
        event.is_error = True  # type: ignore[misc]


def test_tool_approval_resolved_domain_event() -> None:
    now = datetime.now(UTC)
    event = ToolApprovalResolvedDomainEvent(
        approval_id="appr-1",
        tenant_id="corp-acme",
        conversation_id="conv-1",
        status="APPROVED",
        operator_id="operator-1",
        justification="Manual check passed",
        occurred_at=now,
    )
    assert event.approval_id == "appr-1"
    assert event.tenant_id == "corp-acme"
    assert event.conversation_id == "conv-1"
    assert event.status == "APPROVED"
    assert event.operator_id == "operator-1"
    assert event.justification == "Manual check passed"
    assert event.occurred_at == now

    with pytest.raises(AttributeError):
        event.status = "REJECTED"  # type: ignore[misc]
