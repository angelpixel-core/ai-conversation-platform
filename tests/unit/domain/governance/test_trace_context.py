"""Unit tests for TraceContext Value Object (W3C TraceContext standard)."""

from dataclasses import FrozenInstanceError

import pytest
from src.domain.governance.value_objects.trace_context import TraceContext


def test_trace_context_create_root() -> None:
    ctx = TraceContext.create_root(sampled=True)
    assert len(ctx.trace_id) == 32
    assert len(ctx.span_id) == 16
    assert ctx.parent_span_id is None
    assert ctx.trace_flags == 1
    assert ctx.is_sampled is True

    # Test hex validation
    int(ctx.trace_id, 16)
    int(ctx.span_id, 16)


def test_trace_context_to_traceparent() -> None:
    ctx = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        parent_span_id=None,
        trace_flags=1,
    )
    expected = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert ctx.to_traceparent() == expected


def test_trace_context_from_valid_traceparent() -> None:
    raw_header = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    ctx = TraceContext.from_traceparent(raw_header, tracestate="congo=t61rcWkgMzE")
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"
    assert ctx.trace_flags == 1
    assert ctx.tracestate == "congo=t61rcWkgMzE"


def test_trace_context_create_child_span() -> None:
    parent = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        parent_span_id=None,
        trace_flags=1,
        tracestate="vendor=value",
    )
    child = parent.create_child_span()
    assert child.trace_id == parent.trace_id
    assert child.parent_span_id == parent.span_id
    assert child.span_id != parent.span_id
    assert len(child.span_id) == 16
    assert child.trace_flags == parent.trace_flags
    assert child.tracestate == parent.tracestate


def test_trace_context_invalid_traceparent_format() -> None:
    # Too few segments
    with pytest.raises(ValueError, match="Formato traceparent inválido"):
        TraceContext.from_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736")

    # Invalid version (must be 2 hex digits)
    with pytest.raises(ValueError, match="Versión de traceparent no soportada o inválida"):
        TraceContext.from_traceparent("ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")

    # Invalid trace_id length
    with pytest.raises(ValueError, match="trace_id inválido en traceparent"):
        TraceContext.from_traceparent("00-12345-00f067aa0ba902b7-01")

    # Invalid span_id length
    with pytest.raises(ValueError, match="span_id inválido en traceparent"):
        TraceContext.from_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-12345-01")


def test_trace_context_immutability() -> None:
    ctx = TraceContext.create_root()
    with pytest.raises(FrozenInstanceError):
        ctx.trace_id = "new_id"  # type: ignore[misc]
