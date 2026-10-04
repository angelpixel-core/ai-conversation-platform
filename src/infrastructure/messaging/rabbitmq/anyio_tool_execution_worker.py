"""Asynchronous tool execution worker leveraging AnyIO for isolated concurrency."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import anyio

from src.application.shared.ports.event_publisher import EventPublisherPort
from src.domain.shared.events.event_envelope import EventEnvelope
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.events.tool_events import ToolExecutionCompletedDomainEvent
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_result import ToolResult

logger = logging.getLogger(__name__)


class AnyioToolExecutionWorker:
    """Consumes tool execution messages, invokes sandboxed execution, and publishes results."""

    def __init__(
        self,
        runner: SandboxedToolRunnerPort,
        tool_registry: ToolRegistryPort,
        event_publisher: EventPublisherPort | None = None,
        concurrency_limit: int = 5,
    ) -> None:
        self._runner = runner
        self._registry = tool_registry
        self._event_publisher = event_publisher
        self._concurrency_limit = concurrency_limit

    async def process_tool_execution(self, envelope: EventEnvelope | dict[str, Any]) -> ToolResult:
        """Executes a single tool request with security validation and event dispatch."""
        payload: dict[str, Any] = (
            envelope.payload
            if isinstance(envelope, EventEnvelope)
            else envelope.get("payload", envelope)
        )

        tenant_id = str(payload.get("tenant_id", "")).strip()
        conversation_id = str(payload.get("conversation_id", "")).strip()
        call_id = str(payload.get("call_id", "")).strip()
        tool_name = str(payload.get("tool_name", "")).strip()
        arguments = payload.get("arguments", {})
        timeout_seconds = float(payload.get("timeout_seconds", 10.0))

        tool_call = ToolCall(call_id=call_id, tool_name=tool_name, arguments=arguments)

        # Security check: tenant allowance
        tenant_vo = TenantId(tenant_id)
        tool_def = self._registry.get_tool(tool_name)
        if tool_def is None:
            return ToolResult(
                call_id=call_id,
                output=f"Herramienta '{tool_name}' no encontrada en el registro.",
                is_error=True,
                execution_time_ms=0.0,
            )

        if not self._registry.is_tool_allowed(tenant_vo, tool_name):
            return ToolResult(
                call_id=call_id,
                output=f"Herramienta '{tool_name}' no autorizada para el tenant '{tenant_id}'.",
                is_error=True,
                execution_time_ms=0.0,
            )

        result = await self._runner.execute(tool_call, timeout_seconds=timeout_seconds)

        if self._event_publisher is not None:
            self._event_publisher.publish(
                ToolExecutionCompletedDomainEvent(
                    call_id=result.call_id,
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    tool_name=tool_name,
                    is_error=result.is_error,
                    execution_time_ms=result.execution_time_ms,
                    occurred_at=datetime.now(UTC),
                )
            )

        return result

    async def process_batch(
        self, envelopes: Sequence[EventEnvelope | dict[str, Any]]
    ) -> list[ToolResult]:
        """Processes multiple tool execution messages concurrently with AnyIO TaskGroup."""
        results: list[ToolResult | None] = [None] * len(envelopes)
        semaphore = anyio.Semaphore(self._concurrency_limit)

        async def _run_item(idx: int, env: EventEnvelope | dict[str, Any]) -> None:
            async with semaphore:
                res = await self.process_tool_execution(env)
                results[idx] = res

        async with anyio.create_task_group() as tg:
            for i, env in enumerate(envelopes):
                tg.start_soon(_run_item, i, env)

        return [r for r in results if r is not None]
