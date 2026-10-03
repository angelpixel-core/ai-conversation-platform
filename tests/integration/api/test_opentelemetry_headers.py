"""Integration test: OpenTelemetry middleware injecting X-Trace-ID and X-Span-ID headers."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.interfaces.http.api import build_api


@pytest.fixture
def api_client() -> AsyncClient:
    app = build_api(enable_opentelemetry_middleware=True)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_opentelemetry_middleware_injects_trace_headers(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200

    # Ensure response contains X-Trace-ID and X-Span-ID headers
    assert "x-trace-id" in response.headers
    assert "x-span-id" in response.headers

    trace_id = response.headers["x-trace-id"]
    span_id = response.headers["x-span-id"]

    assert len(trace_id) == 32
    assert len(span_id) == 16
    assert trace_id != "0" * 32
    assert span_id != "0" * 16


@pytest.mark.anyio
async def test_opentelemetry_middleware_propagates_w3c_traceparent(
    api_client: AsyncClient,
) -> None:
    custom_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    incoming_traceparent = f"00-{custom_trace_id}-00f067aa0ba902b7-01"

    response = await api_client.get(
        "/health",
        headers={"traceparent": incoming_traceparent},
    )

    assert response.status_code == 200
    assert response.headers.get("x-trace-id") == custom_trace_id
