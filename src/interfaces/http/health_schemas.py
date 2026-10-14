"""Pydantic v2 DTO schemas for system diagnostic health checks."""

from typing import Literal

from pydantic import BaseModel, Field


class ComponentHealthSchema(BaseModel):
    """Diagnostic status for a single system component or external dependency."""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        description="Health status of the component ('healthy', 'unhealthy', 'degraded').",
        examples=["healthy"],
    )
    latency_ms: float = Field(
        description="Round-trip diagnostic probe latency in milliseconds.",
        examples=[8.0],
    )
    engine: str | None = Field(
        default=None,
        description="Underlying technology or provider identifier (e.g. 'mssql', 'rabbitmq').",
        examples=["mssql"],
    )


class HealthChecksSchema(BaseModel):
    """Detailed health check breakdown across critical platform dependencies."""

    database: ComponentHealthSchema = Field(
        description="Health status and latency of the persistent storage layer.",
    )
    broker: ComponentHealthSchema = Field(
        description="Health status and latency of the asynchronous message broker.",
    )
    ai_engine: ComponentHealthSchema = Field(
        description="Health status and latency of the AI model inference engine.",
    )


class HealthCheckResponse(BaseModel):
    """Aggregated health check response for the overall platform."""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        description="Overall platform operational status.",
        examples=["healthy"],
    )
    version: str = Field(
        description="Semantic application version string.",
        examples=["1.0.0"],
    )
    checks: HealthChecksSchema = Field(
        description="Component-level health check and latency breakdown.",
    )
