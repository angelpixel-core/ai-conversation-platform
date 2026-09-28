"""Integration tests for sandboxed tool execution timeout and fault tolerance (Phase 5 RED)."""

import anyio
import pytest

from src.application.tools.commands.execute_sandboxed_tool import (
    ExecuteSandboxedToolCommand,
    ExecuteSandboxedToolHandler,
)
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition
from src.infrastructure.tools.anyio_sandboxed_tool_runner import (
    AnyioSandboxedToolRunner,
)


class SlowToolRegistry(ToolRegistryPort):
    """Registry registering a slow tool to test timeout handling."""

    def __init__(self) -> None:
        self._tool_def = ToolDefinition(
            name="slow_external_api",
            description="Calls a very slow remote service",
            parameters_schema={"type": "object", "properties": {"delay": {"type": "number"}}},
            requires_approval=False,
        )

    def get_tool(self, name: str) -> ToolDefinition | None:
        if name == "slow_external_api":
            return self._tool_def
        return None

    def list_tools(self, tenant_id: TenantId | None = None) -> list[ToolDefinition]:
        return [self._tool_def]

    def is_tool_allowed(self, tenant_id: TenantId, tool_name: str) -> bool:
        return tool_name == "slow_external_api"


async def _slow_handler(delay: float = 2.0) -> dict[str, str]:
    await anyio.sleep(delay)
    return {"status": "finished"}


@pytest.mark.anyio
async def test_sandboxed_tool_runner_aborts_on_timeout() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"slow_external_api": _slow_handler})
    registry = SlowToolRegistry()

    handler = ExecuteSandboxedToolHandler(
        runner=runner,
        tool_registry=registry,
    )

    command = ExecuteSandboxedToolCommand(
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_call=ToolCall(
            call_id="call-timeout-1",
            tool_name="slow_external_api",
            arguments={"delay": 2.0},
        ),
        timeout_seconds=0.1,
    )

    result = await handler.handle(command)

    assert result.call_id == "call-timeout-1"
    assert result.is_error is True
    assert (
        "excedió el límite de tiempo" in result.output.lower() or "timeout" in result.output.lower()
    )
    assert result.execution_time_ms >= 0.0


@pytest.mark.anyio
async def test_sandboxed_tool_runner_handles_exception_gracefully() -> None:
    def _failing_handler() -> None:
        raise RuntimeError("Fatal connection failure to 3rd party service")

    runner = AnyioSandboxedToolRunner(registry_handlers={"failing_tool": _failing_handler})

    tool_call = ToolCall(
        call_id="call-fail-1",
        tool_name="failing_tool",
        arguments={},
    )

    result = await runner.execute(tool_call, timeout_seconds=1.0)

    assert result.call_id == "call-fail-1"
    assert result.is_error is True
    assert "Fatal connection failure" in result.output
