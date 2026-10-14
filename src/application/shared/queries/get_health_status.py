"""Query and QueryHandler for retrieving system diagnostic health status."""

import asyncio
import logging
import time
from dataclasses import dataclass, replace
from typing import ClassVar

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
        cached: Boolean indicating if the result was served from an in-memory TTL cache.
    """

    status: HealthStatus
    version: str
    database: ComponentHealthResult
    broker: ComponentHealthResult
    ai_engine: ComponentHealthResult
    cached: bool = False


class GetHealthStatusQueryHandler(AsyncQueryHandler[GetHealthStatusQuery, HealthStatusResult]):
    """Orchestrates concurrent execution of component health probes with caching and timeouts."""

    DEFAULT_TIMEOUT_SECONDS: ClassVar[float] = 1.5
    DEFAULT_CACHE_TTL_SECONDS: ClassVar[float] = 2.0

    def __init__(
        self,
        database_probe: HealthProbePort,
        broker_probe: HealthProbePort,
        ai_engine_probe: HealthProbePort,
        version: str = "1.0.0",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        """Initialize the query handler with concrete or mock health probes.

        Args:
            database_probe: Probe for checking database connectivity and latency.
            broker_probe: Probe for checking event broker connectivity and latency.
            ai_engine_probe: Probe for checking AI engine availability and latency.
            version: Application semantic version string.
            timeout_seconds: Hard timeout deadline per individual probe in seconds.
            cache_ttl_seconds: Time-to-live for in-memory sliding cache (0.0 disables cache).
        """
        self._database_probe = database_probe
        self._broker_probe = broker_probe
        self._ai_engine_probe = ai_engine_probe
        self._version = version
        self._timeout_seconds = timeout_seconds
        self._cache_ttl_seconds = cache_ttl_seconds

        self._cached_result: HealthStatusResult | None = None
        self._last_evaluated_at: float = 0.0
        self._lock = asyncio.Lock()

    async def handle(
        self, query: GetHealthStatusQuery, *args: object, **kwargs: object
    ) -> HealthStatusResult:
        """Execute or retrieve cached health probes and aggregate the final result.

        Args:
            query: The health status query request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HealthStatusResult: Aggregated diagnostic status.
        """
        if self._cache_ttl_seconds > 0.0:
            now = time.monotonic()
            if (
                self._cached_result is not None
                and (now - self._last_evaluated_at) < self._cache_ttl_seconds
            ):
                return replace(self._cached_result, cached=True)

            async with self._lock:
                now = time.monotonic()
                if (
                    self._cached_result is not None
                    and (now - self._last_evaluated_at) < self._cache_ttl_seconds
                ):
                    return replace(self._cached_result, cached=True)

                fresh_result = await self._execute_probes()
                self._cached_result = fresh_result
                self._last_evaluated_at = time.monotonic()
                return replace(fresh_result, cached=False)

        return await self._execute_probes()

    async def _execute_probes(self) -> HealthStatusResult:
        """Concurrently execute all registered component health probes."""
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
            cached=False,
        )

    async def _safe_probe(
        self, probe: HealthProbePort, default_engine: str | None
    ) -> ComponentHealthResult:
        """Safely execute a health probe with strict fail-fast timeout and exception resilience."""
        start = time.perf_counter()
        try:
            if self._timeout_seconds > 0.0:
                return await asyncio.wait_for(probe.check_health(), timeout=self._timeout_seconds)
            return await probe.check_health()
        except TimeoutError:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "Health probe timed out after %.2fs for %s",
                self._timeout_seconds,
                default_engine or "ai_engine",
            )
            return ComponentHealthResult(
                status="unhealthy",
                latency_ms=latency,
                engine=default_engine,
                details=f"Health probe timed out after {self._timeout_seconds:.2f}s",
            )
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.error("Health probe failed unexpectedly: %s", exc, exc_info=True)
            return ComponentHealthResult(
                status="unhealthy",
                latency_ms=latency,
                engine=default_engine,
                details=str(exc),
            )
