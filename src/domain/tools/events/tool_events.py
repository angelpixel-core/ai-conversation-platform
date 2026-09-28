"""Domain events for Tools, Sandboxed Execution, and Human-in-the-Loop (HITL).

Invariants:
- Immutable by design (@dataclass(frozen=True)).
- Primitives or value objects serializable to JSON Outbox.
- Represent facts that occurred in the past.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ToolCallRequestedDomainEvent:
    """Emitted when an LLM requests execution of an external tool."""

    call_id: str
    tenant_id: str
    conversation_id: str
    tool_name: str
    arguments: dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True)
class ToolApprovalRequiredDomainEvent:
    """Emitted when a tool execution requires human authorization before running."""

    approval_id: str
    tenant_id: str
    conversation_id: str
    tool_name: str
    occurred_at: datetime


@dataclass(frozen=True)
class ToolExecutionCompletedDomainEvent:
    """Emitted when a tool finishes execution in the sandbox."""

    call_id: str
    tenant_id: str
    conversation_id: str
    tool_name: str
    is_error: bool
    execution_time_ms: float
    occurred_at: datetime


@dataclass(frozen=True)
class ToolApprovalResolvedDomainEvent:
    """Emitted when a human operator resolves (approves/rejects) a tool execution request."""

    approval_id: str
    tenant_id: str
    conversation_id: str
    status: str
    operator_id: str
    justification: str | None
    occurred_at: datetime
