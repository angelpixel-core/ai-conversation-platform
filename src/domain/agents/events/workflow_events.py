"""Domain events for Multi-Agent Workflows and State Graphs."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WorkflowStartedDomainEvent:
    """Emitted when a new multi-agent workflow execution is initialized."""

    workflow_id: str
    tenant_id: str
    name: str
    initial_node: str
    occurred_at: datetime


@dataclass(frozen=True)
class SubAgentTaskDelegatedDomainEvent:
    """Emitted when a supervisor node delegates a subtask to an agent specialist."""

    workflow_id: str
    tenant_id: str
    from_node: str
    to_agent: str
    subtask: str
    occurred_at: datetime


@dataclass(frozen=True)
class CheckpointSavedDomainEvent:
    """Emitted when a valid state snapshot is persisted."""

    workflow_id: str
    tenant_id: str
    checkpoint_id: str
    node_id: str
    version: int
    occurred_at: datetime


@dataclass(frozen=True)
class WorkflowApprovalRequiredDomainEvent:
    """Emitted when a subagent tool invocation requires human operator authorization."""

    workflow_id: str
    tenant_id: str
    approval_id: str
    tool_name: str
    occurred_at: datetime


@dataclass(frozen=True)
class WorkflowCompletedDomainEvent:
    """Emitted when the workflow reaches an end state."""

    workflow_id: str
    tenant_id: str
    final_node: str
    occurred_at: datetime
