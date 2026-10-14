"""AI inference engine health probe adapter."""

import inspect
import time

from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
)
from src.application.shared.ports.llm_client import LlmClientPort


class AiEngineHealthProbeAdapter(HealthProbePort):
    """Probes availability and readiness of the underlying LLM client or model catalog."""

    def __init__(self, llm_client: LlmClientPort | None = None) -> None:
        """Initialize adapter.

        Args:
            llm_client: Configured LLM client adapter (optional).
        """
        self._llm_client = llm_client

    async def check_health(self) -> ComponentHealthResult:
        """Probe AI inference engine.

        Returns:
            ComponentHealthResult: AI engine status and latency in milliseconds.
        """
        start = time.perf_counter()
        try:
            if self._llm_client is not None and hasattr(self._llm_client, "check_health"):
                check_fn = getattr(self._llm_client, "check_health")  # noqa: B009
                if callable(check_fn):
                    res = check_fn()
                    if inspect.isawaitable(res):
                        await res
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ComponentHealthResult(
                status="healthy",
                latency_ms=max(latency, 0.1),
                engine=None,  # Intentionally None: client specification omits engine for ai_engine
            )
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ComponentHealthResult(
                status="unhealthy",
                latency_ms=latency,
                engine=None,
                details=str(exc),
            )
