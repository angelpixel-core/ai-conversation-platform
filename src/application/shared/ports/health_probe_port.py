"""Abstract port for probing system component health and latency."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

HealthStatus = Literal["healthy", "unhealthy", "degraded"]


@dataclass(frozen=True)
class ComponentHealthResult:
    """Diagnostic result of a single component health check.

    Attributes:
        status: Current health status ('healthy', 'unhealthy', 'degraded').
        latency_ms: Round-trip probe execution latency in milliseconds.
        engine: Underlying technology or engine identifier (e.g. 'mssql', 'rabbitmq').
        details: Optional diagnostic error message or detail string.
    """

    status: HealthStatus
    latency_ms: float
    engine: str | None = None
    details: str | None = None


class HealthProbePort(ABC):
    """Driven port for executing diagnostic health checks against external dependencies."""

    @abstractmethod
    async def check_health(self) -> ComponentHealthResult:
        """Probe component connectivity and measure execution latency.

        Returns:
            ComponentHealthResult: The diagnostic probe result including status and latency.
        """
        ...
