"""Pydantic schemas for Secure Tool Calling and HITL Approvals HTTP endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateToolApprovalRequest(BaseModel):
    """Request payload to submit a tool execution for approval."""

    conversation_id: str = Field(..., description="ID of conversation triggering the tool call")
    tool_name: str = Field(..., description="Name of the high-privilege tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments for tool call")
    call_id: str | None = Field(default=None, description="Optional tool call ID")


class ToolApprovalDecisionRequest(BaseModel):
    """Request payload for approving or rejecting a pending tool execution."""

    decision: str = Field(..., description="Action to take: 'approve' or 'reject'")
    resolved_by: str = Field(..., description="Operator or security officer identifier")
    reason: str | None = Field(
        default=None,
        description="Justification or rejection explanation for audit log",
    )


class PendingApprovalResponse(BaseModel):
    """Schema representing a tool execution approval request."""

    approval_id: str
    tenant_id: str
    conversation_id: str
    tool_name: str
    arguments: dict[str, Any]
    status: str
    risk_level: str = "CRITICAL"
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    rejection_reason: str | None = None


class ToolExecutionAuditResponse(BaseModel):
    """Schema representing an audited tool execution record."""

    audit_id: str
    call_id: str
    tenant_id: str
    tool_name: str
    status: str
    execution_time_ms: float
    executed_at: datetime
    is_error: bool


__all__ = [
    "CreateToolApprovalRequest",
    "PendingApprovalResponse",
    "ToolApprovalDecisionRequest",
    "ToolExecutionAuditResponse",
]
