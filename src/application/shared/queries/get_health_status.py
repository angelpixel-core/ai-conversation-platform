"""Query and QueryHandler for retrieving system diagnostic health status."""

import asyncio
import logging
from dataclasses import dataclass

from src.application.shared.cqrs.base import AsyncQueryHandler
from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
    HealthStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetHealthStatusQuery:
    """Read-only query requesting the aggregated health status of all system components."""


@dataclass(frozen=True)
class HealthStatusResult:
    """Aggregated health status result across all probed system dependencies.

    Attributes:
        status: Consolidated platform status ('healthy', 'unhealthy', 'degraded').
        version: Semantic application version.
        database: Health status and latency for the database layer.
        broker: Health status and latency for the event broker layer.
        ai_engine: Health status and latency for the AI inference engine.
    """

    status: HealthStatus
    version: str
    database: ComponentHealthResult
    broker: ComponentHealthResult
    ai_engine: ComponentHealthResult


class GetHealthStatusQueryHandler(AsyncQueryHandler[GetHealthStatusQuery, HealthStatusResult]):
    """Orchestrates concurrent execution of component health probes."""

    def __init__(
        self,
        database_probe: HealthProbePort,
        broker_probe: HealthProbePort,
        ai_engine_probe: HealthProbePort,
        version: str = "1.0.0",
    ) -> None:
        """Initialize the query handler with concrete or mock health probes.

        Args:
            database_probe: Probe for checking database connectivity and latency.
            broker_probe: Probe for checking event broker connectivity and latency.
            ai_engine_probe: Probe for checking AI engine availability and latency.
            version: Application semantic version string.
        """
        self._database_probe = database_probe
        self._broker_probe = broker_probe
        self._ai_engine_probe = ai_engine_probe
        self._version = version

    async def handle(
        self, query: GetHealthStatusQuery, *args: object, **kwargs: object
    ) -> HealthStatusResult:
        """Execute all health probes concurrently and aggregate the final result.

        Args:
            query: The health status query request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HealthStatusResult: Aggregated diagnostic status.
        """
        db_task = self._safe_probe(self._database_probe, default_engine="database")
        broker_task = self._safe_probe(self._broker_probe, default_engine="broker")
        ai_task = self._safe_probe(self._ai_engine_probe, default_engine=None)

        db_res, broker_res, ai_res = await asyncio.gather(db_task, broker_task, ai_task)

        overall_status: HealthStatus = "healthy"
        statuses = [db_res.status, broker_res.status, ai_res.status]

        if any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        elif any(s == "degraded" for s in statuses):
            overall_status = "degraded"

        return HealthStatusResult(
            status=overall_status,
            version=self._version,
            database=db_res,
            broker=broker_res,
            ai_engine=ai_res,
        )

    async def _safe_probe(
        self, probe: HealthProbePort, default_engine: str | None
    ) -> ComponentHealthResult:
        """Safely execute a health probe, catching unexpected exceptions to preserve resilience."""
        try:
            return await probe.check_health()
        except Exception as exc:
            logger.error("Health probe failed unexpectedly: %s", exc, exc_info=True)
            return ComponentHealthResult(
                status="unhealthy",
                latency_ms=0.0,
                engine=default_engine,
                details=str(exc),
            )
