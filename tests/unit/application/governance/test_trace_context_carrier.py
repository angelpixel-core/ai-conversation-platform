"""Unit tests for TraceContextCarrier."""

from src.application.shared.telemetry.trace_context_carrier import TraceContextCarrier
from src.domain.governance.value_objects.trace_context import TraceContext


def test_inject_into_headers() -> None:
    carrier = TraceContextCarrier()
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        parent_span_id=None,
        trace_flags=1,
        tracestate="rojo=1",
    )
    headers: dict[str, str] = {"Content-Type": "application/json"}

    injected = carrier.inject_into_headers(ctx, headers)

    assert injected["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert injected["x-trace-id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert injected["x-span-id"] == "00f067aa0ba902b7"
    assert injected["tracestate"] == "rojo=1"


def test_extract_from_headers_valid() -> None:
    carrier = TraceContextCarrier()
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "congo=t61rcWkgMzE",
    }

    ctx = carrier.extract_from_headers(headers)

    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"
    assert ctx.trace_flags == 1
    assert ctx.tracestate == "congo=t61rcWkgMzE"


def test_extract_from_headers_case_insensitive() -> None:
    carrier = TraceContextCarrier()
    headers = {
        "Traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    }

    ctx = carrier.extract_from_headers(headers)

    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"


def test_extract_from_headers_missing_creates_root() -> None:
    carrier = TraceContextCarrier()
    headers: dict[str, str] = {}

    ctx = carrier.extract_from_headers(headers)

    assert len(ctx.trace_id) == 32
    assert len(ctx.span_id) == 16
    assert ctx.is_sampled is True


def test_inject_and_extract_metadata() -> None:
    carrier = TraceContextCarrier()
    ctx = TraceContext.create_root()
    metadata: dict[str, str] = {"event_type": "user_message"}

    injected = carrier.inject_into_metadata(ctx, metadata)
    assert "traceparent" in injected

    extracted = carrier.extract_from_metadata(injected)
    assert extracted.trace_id == ctx.trace_id
    assert extracted.span_id == ctx.span_id
