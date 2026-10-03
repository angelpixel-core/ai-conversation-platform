"""TraceContextCarrier application service template for W3C distributed trace propagation."""

from typing import Any

from src.domain.governance.value_objects.trace_context import TraceContext


class TraceContextCarrier:
    """Serializes and deserializes W3C TraceContext across HTTP headers and message payloads."""

    def inject_into_headers(self, ctx: TraceContext, headers: dict[str, str]) -> dict[str, str]:
        """Injects W3C traceparent and tracing correlation headers into an HTTP headers dict."""
        headers["traceparent"] = ctx.to_traceparent()
        headers["x-trace-id"] = ctx.trace_id
        headers["x-span-id"] = ctx.span_id
        if ctx.tracestate:
            headers["tracestate"] = ctx.tracestate
        return headers

    def extract_from_headers(self, headers: dict[str, str]) -> TraceContext:
        """Extracts TraceContext from HTTP headers case-insensitively or generates a new root."""
        normalized = {k.lower(): v for k, v in headers.items()}
        raw_traceparent = normalized.get("traceparent")
        raw_tracestate = normalized.get("tracestate")

        if raw_traceparent:
            try:
                return TraceContext.from_traceparent(raw_traceparent, tracestate=raw_tracestate)
            except ValueError:
                return TraceContext.create_root()

        return TraceContext.create_root()

    def inject_into_metadata(self, ctx: TraceContext, metadata: dict[str, Any]) -> dict[str, Any]:
        """Injects TraceContext into an envelope metadata dictionary for messaging brokers."""
        metadata["traceparent"] = ctx.to_traceparent()
        metadata["x_trace_id"] = ctx.trace_id
        metadata["x_span_id"] = ctx.span_id
        if ctx.tracestate:
            metadata["tracestate"] = ctx.tracestate
        return metadata

    def extract_from_metadata(self, metadata: dict[str, Any]) -> TraceContext:
        """Extracts TraceContext from envelope metadata dictionary or creates a root."""
        raw_traceparent = metadata.get("traceparent")
        raw_tracestate = metadata.get("tracestate")

        if raw_traceparent:
            try:
                return TraceContext.from_traceparent(
                    str(raw_traceparent),
                    tracestate=str(raw_tracestate) if raw_tracestate else None,
                )
            except ValueError:
                return TraceContext.create_root()

        return TraceContext.create_root()
