"""HTTP DTO Schemas for Enterprise AI Governance and Auditing."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IncidentResponse(BaseModel):
    """Schema representing an audit-grade security or policy violation incident."""

    id: str = Field(description="Unique security incident identifier")
    tenant_id: str = Field(description="Tenant ID owning the incident")
    severity: str = Field(description="Severity grade: LOW, MEDIUM, HIGH, CRITICAL")
    rule_name: str = Field(description="Security rule violated")
    description: str = Field(description="Detailed reason or violation summary")
    prompt_preview: str = Field(description="Redacted snippet of triggering prompt")
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic payload")
    created_at: datetime = Field(description="UTC timestamp of occurrence")


class GovernanceMetricsResponse(BaseModel):
    """Schema representing aggregate safety metrics and incident distributions."""

    total_incidents: int = Field(description="Total count of security incidents")
    by_severity: dict[str, int] = Field(description="Breakdown by severity level")
    by_rule: dict[str, int] = Field(description="Breakdown by rule violation type")
