"""MSSQL database health probe adapter."""

import time

import anyio
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
)


class MssqlHealthProbeAdapter(HealthProbePort):
    """Probes MSSQL / SQLAlchemy database engine connectivity and round-trip query latency."""

    def __init__(
        self,
        engine: Engine,
        engine_name: str = "mssql",
        timeout_seconds: float = 1.5,
    ) -> None:
        """Initialize adapter with SQLAlchemy engine.

        Args:
            engine: SQLAlchemy Engine instance connected to database.
            engine_name: Identifier for the database technology (defaults to 'mssql').
            timeout_seconds: Execution timeout in seconds for the database ping.
        """
        self._engine = engine
        self._engine_name = engine_name
        self._timeout_seconds = timeout_seconds

    async def check_health(self) -> ComponentHealthResult:
        """Execute a lightweight 'SELECT 1' ping in a worker thread and measure latency.

        Returns:
            ComponentHealthResult: Database health status and query latency in milliseconds.
        """
        start = time.perf_counter()
        try:

            def _ping() -> None:
                with self._engine.connect().execution_options(
                    timeout=self._timeout_seconds
                ) as conn:
                    conn.execute(text("SELECT 1"))

            await anyio.to_thread.run_sync(_ping)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ComponentHealthResult(
                status="healthy",
                latency_ms=max(latency, 0.1),
                engine=self._engine_name,
            )
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ComponentHealthResult(
                status="unhealthy",
                latency_ms=latency,
                engine=self._engine_name,
                details=str(exc),
            )
