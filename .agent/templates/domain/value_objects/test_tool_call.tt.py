"""Canonical test template: ToolCall Value Object."""

import pytest
from src.domain.tools.value_objects.tool_call import ToolCall


def test_tool_call_valid() -> None:
    call = ToolCall(
        call_id="call-abc-123",
        tool_name="refund_order",
        arguments={"order_id": "ord-4912", "amount": 150.0},
    )
    assert call.call_id == "call-abc-123"
    assert call.tool_name == "refund_order"
    assert call.arguments["amount"] == 150.0


def test_tool_call_empty_id_raises_error() -> None:
    with pytest.raises(ValueError, match="call_id"):
        ToolCall(call_id="", tool_name="refund", arguments={})
