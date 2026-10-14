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
    """Mock probe for controlled testing of status, latency, calls, and exceptions."""

    status: HealthStatus
    latency_ms: float
    engine: str | None
    delay_seconds: float
    raise_exception: Exception | None
    call_count: int

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
        self.call_count = 0

    async def check_health(self) -> ComponentHealthResult:
        self.call_count += 1
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
        cache_ttl_seconds=0.0,
    )

    result = await handler.handle(GetHealthStatusQuery())

    assert result.status == "healthy"
    assert result.version == "1.0.0"
    assert result.cached is False
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
        cache_ttl_seconds=0.0,
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
        cache_ttl_seconds=0.0,
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
        cache_ttl_seconds=0.0,
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
        cache_ttl_seconds=0.0,
    )

    start = time.perf_counter()
    result = await handler.handle(GetHealthStatusQuery())
    duration = time.perf_counter() - start

    assert result.status == "healthy"
    assert duration < 0.12


@pytest.mark.anyio
async def test_get_health_status_timeout_fail_fast() -> None:
    """Ensure a slow/hanging probe fails fast without blocking the whole health query."""
    db_probe = MockHealthProbe(delay_seconds=0.4)
    broker_probe = MockHealthProbe(status="healthy", latency_ms=2.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=10.0)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
        timeout_seconds=0.05,
        cache_ttl_seconds=0.0,
    )

    start = time.perf_counter()
    result = await handler.handle(GetHealthStatusQuery())
    duration = time.perf_counter() - start

    assert result.status == "unhealthy"
    assert result.database.status == "unhealthy"
    assert result.database.details is not None
    assert "timed out" in result.database.details
    assert result.broker.status == "healthy"
    assert duration < 0.15


@pytest.mark.anyio
async def test_get_health_status_cache_hit_and_miss() -> None:
    """Ensure in-memory TTL cache serves subsequent requests instantly without calling probes."""
    db_probe = MockHealthProbe(status="healthy", latency_ms=10.0, engine="mssql")
    broker_probe = MockHealthProbe(status="healthy", latency_ms=5.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=15.0)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
        cache_ttl_seconds=1.0,
    )

    # 1. First call -> Cache MISS
    res1 = await handler.handle(GetHealthStatusQuery())
    assert res1.cached is False
    assert db_probe.call_count == 1
    assert broker_probe.call_count == 1
    assert ai_probe.call_count == 1

    # 2. Immediate second call -> Cache HIT
    res2 = await handler.handle(GetHealthStatusQuery())
    assert res2.cached is True
    assert res2.status == res1.status
    # Probe calls should NOT increment on cache hit
    assert db_probe.call_count == 1
    assert broker_probe.call_count == 1
    assert ai_probe.call_count == 1


@pytest.mark.anyio
async def test_get_health_status_cache_expiration() -> None:
    """Ensure cache expires after TTL and refreshes probes."""
    db_probe = MockHealthProbe(status="healthy", latency_ms=5.0, engine="mssql")
    broker_probe = MockHealthProbe(status="healthy", latency_ms=2.0, engine="rabbitmq")
    ai_probe = MockHealthProbe(status="healthy", latency_ms=10.0)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
        cache_ttl_seconds=0.05,
    )

    res1 = await handler.handle(GetHealthStatusQuery())
    assert res1.cached is False
    assert db_probe.call_count == 1

    # Wait past TTL
    await asyncio.sleep(0.07)

    res2 = await handler.handle(GetHealthStatusQuery())
    assert res2.cached is False
    assert db_probe.call_count == 2


@pytest.mark.anyio
async def test_get_health_status_thundering_herd_lock() -> None:
    """Ensure concurrent callers on cold cache are deduplicated through lock."""
    db_probe = MockHealthProbe(status="healthy", delay_seconds=0.04)
    broker_probe = MockHealthProbe(status="healthy", delay_seconds=0.04)
    ai_probe = MockHealthProbe(status="healthy", delay_seconds=0.04)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
        cache_ttl_seconds=1.0,
    )

    # Launch 5 concurrent calls simultaneously
    results = await asyncio.gather(*[handler.handle(GetHealthStatusQuery()) for _ in range(5)])

    # All calls succeeded
    assert len(results) == 5
    for r in results:
        assert r.status == "healthy"

    # Only one call actually executed the probes; other 4 were served from cache!
    assert db_probe.call_count == 1
    assert broker_probe.call_count == 1
    assert ai_probe.call_count == 1
