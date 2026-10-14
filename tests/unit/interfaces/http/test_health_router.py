"""Unit tests for the Health HTTP Router."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.shared.ports.health_probe_port import (
    ComponentHealthResult,
    HealthProbePort,
    HealthStatus,
)
from src.application.shared.queries.get_health_status import (
    GetHealthStatusQueryHandler,
)
from src.interfaces.http.routers.health_router import create_health_router


class StubHealthProbe(HealthProbePort):
    """Stub probe returning configured diagnostics."""

    status: HealthStatus
    latency_ms: float
    engine: str | None
    details: str | None

    def __init__(
        self,
        status: HealthStatus = "healthy",
        latency_ms: float = 5.0,
        engine: str | None = None,
        details: str | None = None,
    ) -> None:
        self.status = status
        self.latency_ms = latency_ms
        self.engine = engine
        self.details = details

    async def check_health(self) -> ComponentHealthResult:
        return ComponentHealthResult(
            status=self.status,
            latency_ms=self.latency_ms,
            engine=self.engine,
            details=self.details,
        )


def _build_test_client(
    db_status: HealthStatus = "healthy",
    broker_status: HealthStatus = "healthy",
    ai_status: HealthStatus = "healthy",
) -> TestClient:
    db_probe = StubHealthProbe(status=db_status, latency_ms=8.0, engine="mssql")
    broker_probe = StubHealthProbe(status=broker_status, latency_ms=4.0, engine="rabbitmq")
    ai_probe = StubHealthProbe(status=ai_status, latency_ms=32.0, engine=None)

    handler = GetHealthStatusQueryHandler(
        database_probe=db_probe,
        broker_probe=broker_probe,
        ai_engine_probe=ai_probe,
        version="1.0.0",
    )

    app = FastAPI()
    app.include_router(create_health_router(handler))
    return TestClient(app)


def test_get_health_healthy_response_contract() -> None:
    """Ensure GET /health returns 200 OK and conforms to the enriched contract."""
    client = _build_test_client()
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "healthy"
    assert payload["version"] == "1.0.0"
    assert "checks" in payload

    # Database check assertions
    db_check = payload["checks"]["database"]
    assert db_check["status"] == "healthy"
    assert db_check["latency_ms"] == 8.0
    assert db_check["engine"] == "mssql"

    # Broker check assertions
    broker_check = payload["checks"]["broker"]
    assert broker_check["status"] == "healthy"
    assert broker_check["latency_ms"] == 4.0
    assert broker_check["engine"] == "rabbitmq"

    # AI Engine check assertions (engine must be omitted, not null)
    ai_check = payload["checks"]["ai_engine"]
    assert ai_check["status"] == "healthy"
    assert ai_check["latency_ms"] == 32.0
    assert "engine" not in ai_check, "engine should be excluded when None"


def test_get_health_unhealthy_status() -> None:
    """Ensure platform reports 'unhealthy' if a dependency fails."""
    client = _build_test_client(db_status="unhealthy")
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "unhealthy"
    assert payload["checks"]["database"]["status"] == "unhealthy"
    assert payload["checks"]["broker"]["status"] == "healthy"
