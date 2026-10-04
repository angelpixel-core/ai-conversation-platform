"""Unit tests for ExecuteSandboxedToolCommandHandler."""

import pytest

from src.application.shared.ports.event_publisher import EventPublisherPort
from src.application.tools.commands.execute_sandboxed_tool import (
    ExecuteSandboxedToolCommand,
    ExecuteSandboxedToolCommandHandler,
)
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.events.tool_events import ToolExecutionCompletedDomainEvent
from src.domain.tools.exceptions import ToolNotFoundError
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition
from src.domain.tools.value_objects.tool_result import ToolResult


class FakeSandboxedRunner(SandboxedToolRunnerPort):
    def __init__(self, output: str = "ok", is_error: bool = False, latency: float = 12.0) -> None:
        self.output = output
        self.is_error = is_error
        self.latency = latency
        self.executed_calls: list[ToolCall] = []

    async def execute(self, tool_call: ToolCall, timeout_seconds: float = 10.0) -> ToolResult:
        self.executed_calls.append(tool_call)
        return ToolResult(
            call_id=tool_call.call_id,
            output=self.output,
            is_error=self.is_error,
            execution_time_ms=self.latency,
        )


class FakeRegistry(ToolRegistryPort):
    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}
        self.allowed: dict[str, set[str]] = {}

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self.tools.get(name)

    def list_tools(self, tenant_id: TenantId | None = None) -> list[ToolDefinition]:
        return list(self.tools.values())

    def is_tool_allowed(self, tenant_id: TenantId, tool_name: str) -> bool:
        return tool_name in self.allowed.get(str(tenant_id), set())


class FakePublisher(EventPublisherPort):
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


@pytest.mark.anyio
async def test_execute_sandboxed_tool_handler_success() -> None:
    runner = FakeSandboxedRunner(output='{"result": "22°C"}', latency=15.0)
    registry = FakeRegistry()
    registry.tools["get_weather"] = ToolDefinition(
        name="get_weather",
        description="weather info",
        parameters_schema={},
    )
    registry.allowed["corp-acme"] = {"get_weather"}
    publisher = FakePublisher()

    handler = ExecuteSandboxedToolCommandHandler(
        runner=runner,
        tool_registry=registry,
        event_publisher=publisher,
    )

    call = ToolCall(call_id="c-1", tool_name="get_weather", arguments={"city": "Madrid"})
    cmd = ExecuteSandboxedToolCommand(
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_call=call,
        timeout_seconds=5.0,
    )

    res = await handler.handle(cmd)

    assert res.call_id == "c-1"
    assert res.output == '{"result": "22°C"}'
    assert res.is_error is False
    assert res.execution_time_ms == 15.0

    assert len(runner.executed_calls) == 1
    assert runner.executed_calls[0].call_id == "c-1"

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert isinstance(event, ToolExecutionCompletedDomainEvent)
    assert event.call_id == "c-1"
    assert event.tool_name == "get_weather"
    assert event.is_error is False


@pytest.mark.anyio
async def test_execute_sandboxed_tool_not_found_raises_tool_not_found_error() -> None:
    runner = FakeSandboxedRunner()
    registry = FakeRegistry()
    handler = ExecuteSandboxedToolCommandHandler(
        runner=runner,
        tool_registry=registry,
    )

    call = ToolCall(call_id="c-1", tool_name="unknown_tool", arguments={})
    cmd = ExecuteSandboxedToolCommand(
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_call=call,
    )

    with pytest.raises(ToolNotFoundError, match="no encontrada"):
        await handler.handle(cmd)


@pytest.mark.anyio
async def test_execute_sandboxed_tool_not_allowed_for_tenant_raises_value_error() -> None:
    runner = FakeSandboxedRunner()
    registry = FakeRegistry()
    registry.tools["restricted_tool"] = ToolDefinition(
        name="restricted_tool",
        description="restricted",
        parameters_schema={},
    )
    # Not adding to registry.allowed["corp-acme"]
    handler = ExecuteSandboxedToolCommandHandler(
        runner=runner,
        tool_registry=registry,
    )

    call = ToolCall(call_id="c-1", tool_name="restricted_tool", arguments={})
    cmd = ExecuteSandboxedToolCommand(
        tenant_id="corp-acme",
        conversation_id="conv-1",
        tool_call=call,
    )

    with pytest.raises(ValueError, match="no autorizada"):
        await handler.handle(cmd)
