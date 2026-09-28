"""Unit tests for ToolCall and ToolResult Value Objects."""

from datetime import datetime

import pytest

from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_result import ToolResult


def test_tool_call_valid_creation() -> None:
    call = ToolCall(
        call_id="call-abc-123",
        tool_name="refund_order",
        arguments={"order_id": "ord-4912", "amount": 150.0},
    )
    assert call.call_id == "call-abc-123"
    assert call.tool_name == "refund_order"
    assert call.arguments == {"order_id": "ord-4912", "amount": 150.0}
    assert isinstance(call.created_at, datetime)


def test_tool_call_empty_call_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="call_id"):
        ToolCall(call_id="", tool_name="refund", arguments={})


def test_tool_call_empty_tool_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="tool_name"):
        ToolCall(call_id="call-1", tool_name="  ", arguments={})


def test_tool_call_invalid_arguments_type_raises_value_error() -> None:
    with pytest.raises(ValueError, match="argumentos"):
        ToolCall(call_id="call-1", tool_name="refund", arguments="invalid")  # type: ignore[arg-type]


def test_tool_call_immutability() -> None:
    call = ToolCall(call_id="c-1", tool_name="echo", arguments={})
    with pytest.raises(AttributeError):
        call.tool_name = "other"  # type: ignore[misc]


def test_tool_result_valid_creation() -> None:
    res = ToolResult(
        call_id="call-abc-123",
        output='{"status": "refunded", "tx_id": "tx-999"}',
        is_error=False,
        execution_time_ms=45.2,
    )
    assert res.call_id == "call-abc-123"
    assert res.output == '{"status": "refunded", "tx_id": "tx-999"}'
    assert res.is_error is False
    assert res.execution_time_ms == 45.2


def test_tool_result_empty_call_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="call_id"):
        ToolResult(call_id="", output="err", is_error=True)


def test_tool_result_negative_execution_time_raises_value_error() -> None:
    with pytest.raises(ValueError, match="execution_time_ms"):
        ToolResult(call_id="call-1", output="err", execution_time_ms=-5.0)


def test_tool_result_immutability() -> None:
    res = ToolResult(call_id="call-1", output="ok")
    with pytest.raises(AttributeError):
        res.output = "modified"  # type: ignore[misc]
