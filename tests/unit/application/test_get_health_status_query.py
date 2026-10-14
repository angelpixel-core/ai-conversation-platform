"""Unit tests for GetHealthStatusQueryHandler."""

import asyncio
import time

import pytest

from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
    HealthStatus,
)
from src.application.shared.queries.get_health_status import (
    GetHealthStatusQuery,
    GetHealthStatusQueryHandler,
)


class MockHealthProbe(HealthProbePort):
    """Mock probe for controlled testing of status, latency and exceptions."""

    status: HealthStatus
    latency_ms: float
    engine: str | None
    delay_seconds: float
    raise_exception: Exception | None

    def __init__(
        self,
        status: HealthStatus = "healthy",
        latency_ms: float = 5.0,
        engine: str | None = None,
        delay_seconds: float = 0.0,
        raise_exception: Exception | None = None,
    ) -> None:
        self.status = status
        self.latency_ms = latency_ms
        self.engine = engine
        self.delay_seconds = delay_seconds
        self.raise_exception = raise_exception

    async def check_health(self) -> ComponentHealthResult:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if self.raise_exception:
            raise self.raise_exception
        return ComponentHealthResult(
            status=self.status,
            latency_ms=self.latency_ms,
            engine=self.engine,
        )


@pytest.mark.anyio
async def test_get_health_status_all_healthy() -> None:
    """Ensure overall status is 'healthy' when all probes succeed."""
    db_probe = MockHealthProbe(status="healthy", latency_ms=8.0, engine="mssql")
    broker_probe = MockHealthProbe(status="healthy", latency_ms=4.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=32.0, engine=None)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
        version="1.0.0",
    )

    result = await handler.handle(GetHealthStatusQuery())

    assert result.status == "healthy"
    assert result.version == "1.0.0"
    assert result.database.status == "healthy"
    assert result.database.latency_ms == 8.0
    assert result.database.engine == "mssql"

    assert result.broker.status == "healthy"
    assert result.broker.latency_ms == 4.0
    assert result.broker.engine == "rabbitmq"

    assert result.ai_engine.status == "healthy"
    assert result.ai_engine.latency_ms == 32.0
    assert result.ai_engine.engine is None


@pytest.mark.anyio
async def test_get_health_status_one_unhealthy() -> None:
    """Ensure overall status is 'unhealthy' if database fails."""
    db_probe = MockHealthProbe(status="unhealthy", latency_ms=100.0, engine="mssql")
    broker_probe = MockHealthProbe(status="healthy", latency_ms=3.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=25.0)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
    )

    result = await handler.handle(GetHealthStatusQuery())

    assert result.status == "unhealthy"
    assert result.database.status == "unhealthy"
    assert result.broker.status == "healthy"


@pytest.mark.anyio
async def test_get_health_status_degraded_when_no_unhealthy() -> None:
    """Ensure overall status is 'degraded' if a probe reports degraded."""
    db_probe = MockHealthProbe(status="healthy", latency_ms=5.0, engine="mssql")
    broker_probe = MockHealthProbe(status="degraded", latency_ms=45.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=10.0)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
    )

    result = await handler.handle(GetHealthStatusQuery())

    assert result.status == "degraded"
    assert result.broker.status == "degraded"


@pytest.mark.anyio
async def test_get_health_status_handles_unexpected_exception() -> None:
    """Ensure an unhandled exception in a probe is caught and marked as unhealthy."""
    db_probe = MockHealthProbe(raise_exception=ConnectionRefusedError("Database unreachable"))
    broker_probe = MockHealthProbe(status="healthy", latency_ms=2.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=15.0)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
    )

    result = await handler.handle(GetHealthStatusQuery())

    assert result.status == "unhealthy"
    assert result.database.status == "unhealthy"
    assert result.database.details == "Database unreachable"
    assert result.broker.status == "healthy"


@pytest.mark.anyio
async def test_get_health_status_concurrent_execution() -> None:
    """Ensure probes execute concurrently via asyncio.gather."""
    delay = 0.05
    db_probe = MockHealthProbe(delay_seconds=delay)
    broker_probe = MockHealthProbe(delay_seconds=delay)
    ai_probe = MockHealthProbe(delay_seconds=delay)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
    )

    start = time.perf_counter()
    result = await handler.handle(GetHealthStatusQuery())
    duration = time.perf_counter() - start

    assert result.status == "healthy"
    # Should take ~0.05s, definitely less than sequential 0.15s
    assert duration < 0.12
