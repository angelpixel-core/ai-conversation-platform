"""Pydantic v2 DTO schemas for multi-agent workflows and checkpoints."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class StartWorkflowRequest(BaseModel):
    """Payload to launch a multi-agent state graph execution."""

    name: str = Field(
        default="research_and_audit_pipeline",
        description="Descriptive name of the workflow execution",
    )
    initial_node: str = Field(default="supervisor", description="Entry node in graph")
    initial_state: dict[str, Any] = Field(
        default_factory=dict, description="Initial global state data"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "name" not in data and "graph_name" in data:
                data["name"] = data["graph_name"]
            if "initial_state" not in data and "initial_context" in data:
                data["initial_state"] = data["initial_context"]
        return data


class ResumeWorkflowRequest(BaseModel):
    """Payload to resume an approval-gated or paused workflow."""

    resumed_state_updates: dict[str, Any] = Field(
        default_factory=dict, description="Operator inputs or resolved tool output updates"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "resumed_state_updates" not in data:
                if "updated_context" in data:
                    data["resumed_state_updates"] = data["updated_context"]
                elif "initial_state" in data:
                    data["resumed_state_updates"] = data["initial_state"]
        return data


class WorkflowStateResponse(BaseModel):
    """DTO response for workflow instance state."""

    workflow_id: str
    tenant_id: str
    name: str
    current_node: str
    status: str
    version: int
    state_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkflowCheckpointResponse(BaseModel):
    """DTO response representing an immutable state snapshot checkpoint."""

    checkpoint_id: str
    workflow_id: str
    tenant_id: str
    current_node: str
    version: int
    status: str
    state_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class AgentActivityEventSchema(BaseModel):
    """SSE event payload for streaming agent handoffs and subagent activity."""

    event_type: str
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


AgentActivityEventResponse = AgentActivityEventSchema

__all__ = [
    "AgentActivityEventResponse",
    "AgentActivityEventSchema",
    "ResumeWorkflowRequest",
    "StartWorkflowRequest",
    "WorkflowCheckpointResponse",
    "WorkflowStateResponse",
]
