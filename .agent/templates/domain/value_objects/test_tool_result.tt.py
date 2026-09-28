"""Canonical test template: ToolResult Value Object."""

import pytest
from src.domain.tools.value_objects.tool_result import ToolResult


def test_tool_result_success() -> None:
    res = ToolResult(
        call_id="call-abc-123",
        output='{"status": "refunded", "tx_id": "tx-999"}',
        is_error=False,
        execution_time_ms=45.2,
    )
    assert res.call_id == "call-abc-123"
    assert res.is_error is False
    assert res.execution_time_ms == 45.2


def test_tool_result_negative_latency_raises_error() -> None:
    with pytest.raises(ValueError, match="execution_time_ms"):
        ToolResult(call_id="call-1", output="err", execution_time_ms=-1.0)
