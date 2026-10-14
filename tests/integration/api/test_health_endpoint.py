"""Integration tests for the /health diagnostic endpoint."""

from fastapi.testclient import TestClient

from src.container import create_app_container
from src.infrastructure.shared.config.settings import PersistenceDriver, Settings


def test_health_endpoint_integration_with_telemetry_and_tenancy() -> None:
    """Ensure /health endpoint functions smoothly with OpenTelemetry and Tenant middlewares."""
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY,
        ENABLE_TENANT_MIDDLEWARE=True,
        ENABLE_OPENTELEMETRY=True,
    )
    container = create_app_container(settings=settings)
    client = TestClient(container.fastapi_app)

    # Note: Health endpoint should be publicly accessible without requiring X-Tenant-ID header
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Trace-ID" in response.headers
    assert "X-Span-ID" in response.headers
    assert response.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate"
    assert response.headers.get("X-Health-Cache") == "MISS"

    # Immediate second call should be served from memory cache (HIT)
    response_cached = client.get("/health")
    assert response_cached.status_code == 200
    assert response_cached.headers.get("X-Health-Cache") == "HIT"

    body = response.json()
    assert body["status"] == "healthy"
    assert body["version"] == "1.0.0"

    checks = body["checks"]
    assert checks["database"]["status"] == "healthy"
    assert checks["database"]["engine"] == "mssql"
    assert checks["database"]["latency_ms"] >= 0.0

    assert checks["broker"]["status"] == "healthy"
    assert checks["broker"]["engine"] == "rabbitmq"
    assert checks["broker"]["latency_ms"] >= 0.0

    assert checks["ai_engine"]["status"] == "healthy"
    assert "engine" not in checks["ai_engine"]
    assert checks["ai_engine"]["latency_ms"] >= 0.0
