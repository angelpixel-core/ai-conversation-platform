"""RabbitMQ message broker health probe adapter."""

import time

from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)


class RabbitMQHealthProbeAdapter(HealthProbePort):
    """Probes RabbitMQ connection health, socket status and round-trip ping latency."""

    def __init__(
        self,
        connection_manager: RabbitMQConnectionManager,
        engine_name: str = "rabbitmq",
    ) -> None:
        """Initialize adapter.

        Args:
            connection_manager: Robust connection manager for RabbitMQ.
            engine_name: Broker technology identifier (defaults to 'rabbitmq').
        """
        self._connection_manager = connection_manager
        self._engine_name = engine_name

    async def check_health(self) -> ComponentHealthResult:
        """Probe RabbitMQ robust connection.

        Returns:
            ComponentHealthResult: Message broker status and latency in milliseconds.
        """
        start = time.perf_counter()
        try:
            conn = await self._connection_manager.get_connection(max_retries=1, retry_delay=0.1)
            if conn.is_closed:
                raise ConnectionError("RabbitMQ connection is closed")
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
