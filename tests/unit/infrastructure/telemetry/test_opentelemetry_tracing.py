"""Unit tests for OpenTelemetry tracing configuration and W3C propagation."""

from opentelemetry import trace
from opentelemetry.trace import Tracer

from src.infrastructure.telemetry.opentelemetry_config import (
    get_tracer,
    setup_opentelemetry,
)


def test_setup_opentelemetry_configures_tracer_provider() -> None:
    provider = setup_opentelemetry(service_name="test-chatbot-api")
    assert provider is not None

    tracer = get_tracer("test.module")
    assert isinstance(tracer, Tracer)

    with tracer.start_as_current_span("test_span") as span:
        span_ctx = span.get_span_context()
        assert span_ctx.is_valid
        assert span_ctx.trace_id != 0
        assert span_ctx.span_id != 0

        # W3C trace id is 32 hex chars, span id is 16 hex chars
        trace_id_hex = trace.format_trace_id(span_ctx.trace_id)
        span_id_hex = trace.format_span_id(span_ctx.span_id)
        assert len(trace_id_hex) == 32
        assert len(span_id_hex) == 16
