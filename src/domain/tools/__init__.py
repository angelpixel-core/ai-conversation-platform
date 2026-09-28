"""Domain package for Tools, Sandboxed Execution, and Human-in-the-Loop (HITL)."""

from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.events.tool_events import (
    ToolApprovalRequiredDomainEvent,
    ToolApprovalResolvedDomainEvent,
    ToolCallRequestedDomainEvent,
    ToolExecutionCompletedDomainEvent,
)
from src.domain.tools.exceptions import (
    InvalidApprovalStateError,
    ToolExecutionError,
    ToolNotFoundError,
)
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition
from src.domain.tools.value_objects.tool_result import ToolResult

__all__ = [
    "ApprovalStatus",
    "InvalidApprovalStateError",
    "SandboxedToolRunnerPort",
    "ToolApprovalRepositoryPort",
    "ToolApprovalRequest",
    "ToolApprovalRequiredDomainEvent",
    "ToolApprovalResolvedDomainEvent",
    "ToolCall",
    "ToolCallRequestedDomainEvent",
    "ToolDefinition",
    "ToolExecutionCompletedDomainEvent",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolRegistryPort",
    "ToolResult",
]
