"""Unit tests for AnyioToolExecutionWorker."""

import pytest

from src.application.shared.ports.event_publisher import EventPublisher
from src.domain.shared.events.event_envelope import EventEnvelope
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.events.tool_events import ToolExecutionCompletedDomainEvent
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition
from src.domain.tools.value_objects.tool_result import ToolResult
from src.infrastructure.messaging.rabbitmq.anyio_tool_execution_worker import (
    AnyioToolExecutionWorker,
)


class FakeRunner(SandboxedToolRunnerPort):
    def __init__(self) -> None:
        self.executed: list[ToolCall] = []

    async def execute(self, tool_call: ToolCall, timeout_seconds: float = 10.0) -> ToolResult:
        self.executed.append(tool_call)
        return ToolResult(
            call_id=tool_call.call_id,
            output=f"Output for {tool_call.tool_name}",
            is_error=False,
            execution_time_ms=10.0,
        )


class FakeRegistry(ToolRegistryPort):
    def __init__(self) -> None:
        self.tools = {
            "get_weather": ToolDefinition(
                name="get_weather",
                description="Weather",
                parameters_schema={},
            )
        }
        self.allowed: dict[str, set[str]] = {"corp-acme": {"get_weather"}}

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self.tools.get(name)

    def list_tools(self, tenant_id: TenantId | None = None) -> list[ToolDefinition]:
        return list(self.tools.values())

    def is_tool_allowed(self, tenant_id: TenantId, tool_name: str) -> bool:
        return tool_name in self.allowed.get(str(tenant_id), set())


class FakePublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


@pytest.mark.anyio
async def test_worker_processes_single_envelope() -> None:
    runner = FakeRunner()
    registry = FakeRegistry()
    publisher = FakePublisher()
    worker = AnyioToolExecutionWorker(
        runner=runner,
        tool_registry=registry,
        event_publisher=publisher,
    )

    envelope = EventEnvelope.create(
        event_type="tools.execute",
        payload={
            "tenant_id": "corp-acme",
            "conversation_id": "conv-1",
            "call_id": "call-1",
            "tool_name": "get_weather",
            "arguments": {"city": "Santiago"},
            "timeout_seconds": 5.0,
        },
    )

    result = await worker.process_tool_execution(envelope)

    assert result.call_id == "call-1"
    assert result.is_error is False
    assert "Output for get_weather" in result.output
    assert len(runner.executed) == 1

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert isinstance(event, ToolExecutionCompletedDomainEvent)
    assert event.call_id == "call-1"
    assert event.tool_name == "get_weather"


@pytest.mark.anyio
async def test_worker_processes_batch_concurrently() -> None:
    runner = FakeRunner()
    registry = FakeRegistry()
    publisher = FakePublisher()
    worker = AnyioToolExecutionWorker(
        runner=runner,
        tool_registry=registry,
        event_publisher=publisher,
        concurrency_limit=3,
    )

    envelopes = [
        EventEnvelope.create(
            event_type="tools.execute",
            payload={
                "tenant_id": "corp-acme",
                "conversation_id": "conv-1",
                "call_id": f"call-{i}",
                "tool_name": "get_weather",
                "arguments": {"city": f"City-{i}"},
            },
        )
        for i in range(5)
    ]

    results = await worker.process_batch(envelopes)

    assert len(results) == 5
    assert len(runner.executed) == 5
    assert len(publisher.events) == 5


@pytest.mark.anyio
async def test_worker_handles_unauthorized_tool() -> None:
    runner = FakeRunner()
    registry = FakeRegistry()
    registry.tools["unauthorized_tool"] = ToolDefinition(
        name="unauthorized_tool",
        description="unauthorized",
        parameters_schema={},
    )
    # is_tool_allowed returns False for corp-acme
    worker = AnyioToolExecutionWorker(runner=runner, tool_registry=registry)

    envelope = {
        "tenant_id": "corp-acme",
        "conversation_id": "conv-1",
        "call_id": "call-99",
        "tool_name": "unauthorized_tool",
        "arguments": {},
    }

    result = await worker.process_tool_execution(envelope)

    assert result.call_id == "call-99"
    assert result.is_error is True
    assert "no autorizada" in result.output
