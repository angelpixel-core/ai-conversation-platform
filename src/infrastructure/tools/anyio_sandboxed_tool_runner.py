"""AnyioSandboxedToolRunner executes external tools with strict timeout guards using AnyIO."""

import inspect
import logging
import time
from collections.abc import Callable
from typing import Any

import anyio

from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_result import ToolResult

logger = logging.getLogger(__name__)


class AnyioSandboxedToolRunnerAdapter(SandboxedToolRunnerPort):
    """Executes external tools with strict timeout guards using AnyIO."""

    def __init__(self, registry_handlers: dict[str, Callable[..., Any]] | None = None) -> None:
        self._handlers = registry_handlers or {}

    async def execute(self, tool_call: ToolCall, timeout_seconds: float = 10.0) -> ToolResult:
        handler = self._handlers.get(tool_call.tool_name)
        if handler is None:
            return ToolResult(
                call_id=tool_call.call_id,
                output=f"Herramienta '{tool_call.tool_name}' no encontrada en el sandbox.",
                is_error=True,
                execution_time_ms=0.0,
            )

        start_time = time.perf_counter()
        try:
            with anyio.fail_after(timeout_seconds):
                if inspect.iscoroutinefunction(handler):
                    output = await handler(**tool_call.arguments)
                else:
                    output = handler(**tool_call.arguments)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                call_id=tool_call.call_id,
                output=str(output),
                is_error=False,
                execution_time_ms=round(elapsed_ms, 2),
            )
        except TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                call_id=tool_call.call_id,
                output=f"La herramienta excedió el límite de tiempo de {timeout_seconds}s.",
                is_error=True,
                execution_time_ms=round(elapsed_ms, 2),
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                call_id=tool_call.call_id,
                output=f"Error durante la ejecución de la herramienta: {exc}",
                is_error=True,
                execution_time_ms=round(elapsed_ms, 2),
            )


__all__ = ["AnyioSandboxedToolRunnerAdapter"]
