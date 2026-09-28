"""Execute sandboxed tool command and handler for isolated tool execution."""

from dataclasses import dataclass
from datetime import UTC, datetime

from src.application.shared.ports.event_publisher import EventPublisher
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.events.tool_events import ToolExecutionCompletedDomainEvent
from src.domain.tools.exceptions import ToolNotFoundError
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall


@dataclass(frozen=True)
class ExecuteSandboxedToolCommand:
    """Command to execute an authorized tool call in a sandboxed runner."""

    tenant_id: str
    conversation_id: str
    tool_call: ToolCall
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class ExecuteSandboxedToolResult:
    """Result of sandboxed tool execution."""

    call_id: str
    output: str
    is_error: bool
    execution_time_ms: float


class ExecuteSandboxedToolHandler:
    """Handles sandboxed execution of tools with timeouts and permission checks."""

    def __init__(
        self,
        runner: SandboxedToolRunnerPort,
        tool_registry: ToolRegistryPort,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._runner = runner
        self._registry = tool_registry
        self._event_publisher = event_publisher

    async def handle(self, command: ExecuteSandboxedToolCommand) -> ExecuteSandboxedToolResult:
        tenant_id = TenantId(command.tenant_id)
        tool_def = self._registry.get_tool(command.tool_call.tool_name)
        if tool_def is None:
            raise ToolNotFoundError(
                f"Herramienta '{command.tool_call.tool_name}' no encontrada en el registro."
            )

        if not self._registry.is_tool_allowed(tenant_id, command.tool_call.tool_name):
            raise ValueError(
                f"Herramienta '{command.tool_call.tool_name}' no autorizada "
                f"para el tenant '{command.tenant_id}'."
            )

        result = await self._runner.execute(
            command.tool_call, timeout_seconds=command.timeout_seconds
        )

        if self._event_publisher is not None:
            self._event_publisher.publish(
                ToolExecutionCompletedDomainEvent(
                    call_id=result.call_id,
                    tenant_id=command.tenant_id,
                    conversation_id=command.conversation_id,
                    tool_name=command.tool_call.tool_name,
                    is_error=result.is_error,
                    execution_time_ms=result.execution_time_ms,
                    occurred_at=datetime.now(UTC),
                )
            )

        return ExecuteSandboxedToolResult(
            call_id=result.call_id,
            output=result.output,
            is_error=result.is_error,
            execution_time_ms=result.execution_time_ms,
        )
