"""In-memory broker health probe adapter."""

import time

from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
)


class InMemoryBrokerHealthProbeAdapter(HealthProbePort):
    """In-memory diagnostic broker probe for testing and local development environments."""

    def __init__(self, engine_name: str = "rabbitmq") -> None:
        """Initialize adapter.

        Args:
            engine_name: Technology name to report (defaults to 'rabbitmq' to conform
                with standard API contract).
        """
        self._engine_name = engine_name

    async def check_health(self) -> ComponentHealthResult:
        """Execute in-memory broker health check.

        Returns:
            ComponentHealthResult: In-memory broker health status and minimal latency.
        """
        start = time.perf_counter()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealthResult(
            status="healthy",
            latency_ms=max(latency, 0.1),
            engine=self._engine_name,
        )
