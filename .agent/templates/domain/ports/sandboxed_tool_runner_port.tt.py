"""Canonical template: SandboxedToolRunnerPort Driven Port."""

from abc import ABC, abstractmethod

from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_result import ToolResult


class SandboxedToolRunnerPort(ABC):
    """Abstract port for safely executing tools within an isolated, timeout-guarded environment."""

    @abstractmethod
    async def execute(self, tool_call: ToolCall, timeout_seconds: float = 10.0) -> ToolResult:
        """Executes the given tool call within a sandboxed context and returns the execution result."""
        ...
