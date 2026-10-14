"""System health and observability HTTP Router."""

from fastapi import APIRouter, status

from src.application.shared.queries.get_health_status import (
    GetHealthStatusQuery,
    GetHealthStatusQueryHandler,
)
from src.interfaces.http.health_schemas import (
    ComponentHealthSchema,
    HealthCheckResponse,
    HealthChecksSchema,
)


def create_health_router(health_handler: GetHealthStatusQueryHandler) -> APIRouter:
    """Factory creating APIRouter for system health and dependency diagnostics.

    Args:
        health_handler: CQRS QueryHandler orchestrating health probe checks.

    Returns:
        APIRouter: Configured FastAPI router with /health endpoint.
    """
    router = APIRouter(tags=["Observability"])

    @router.get(
        "/health",
        response_model=HealthCheckResponse,
        response_model_exclude_none=True,
        status_code=status.HTTP_200_OK,
        summary="Platform Health and Dependency Diagnostics",
        description=(
            "Aggregates operational status, latency in milliseconds, and technology details "
            "for persistent storage, message broker, and AI inference engines."
        ),
    )
    async def get_health() -> HealthCheckResponse:
        result = await health_handler.handle(GetHealthStatusQuery())
        return HealthCheckResponse(
            status=result.status,
            version=result.version,
            checks=HealthChecksSchema(
                database=ComponentHealthSchema(
                    status=result.database.status,
                    latency_ms=result.database.latency_ms,
                    engine=result.database.engine,
                ),
                broker=ComponentHealthSchema(
                    status=result.broker.status,
                    latency_ms=result.broker.latency_ms,
                    engine=result.broker.engine,
                ),
                ai_engine=ComponentHealthSchema(
                    status=result.ai_engine.status,
                    latency_ms=result.ai_engine.latency_ms,
                    engine=result.ai_engine.engine,
                ),
            ),
        )

    return router
