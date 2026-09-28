"""Canonical test template: SandboxedToolRunnerPort Driven Port."""

import pytest
from src.domain.tools.ports.sandboxed_tool_runner_port import SandboxedToolRunnerPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_result import ToolResult


class FakeSandboxedRunner(SandboxedToolRunnerPort):
    async def execute(self, tool_call: ToolCall, timeout_seconds: float = 10.0) -> ToolResult:
        return ToolResult(
            call_id=tool_call.call_id,
            output=f"executed {tool_call.tool_name}",
            is_error=False,
            execution_time_ms=12.5,
        )


@pytest.mark.anyio
async def test_sandboxed_runner_contract() -> None:
    runner: SandboxedToolRunnerPort = FakeSandboxedRunner()
    call = ToolCall(call_id="c-1", tool_name="echo", arguments={"text": "hello"})
    result = await runner.execute(call)

    assert result.call_id == "c-1"
    assert result.is_error is False
    assert "echo" in result.output
