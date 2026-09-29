"""OpenTelemetry HTTP middleware for distributed trace context propagation."""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from opentelemetry import trace
from opentelemetry.propagate import extract
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.telemetry.opentelemetry_config import get_tracer, setup_opentelemetry


class OpenTelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware extracting W3C trace contexts and injecting X-Trace-ID and X-Span-ID headers."""

    def __init__(self, app: Callable[..., Any] | Any, service_name: str = "chatbot-api") -> None:
        super().__init__(app)
        setup_opentelemetry(service_name=service_name)
        self._tracer = get_tracer("http.middleware")

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Processes request within an active OpenTelemetry span and injects correlation headers."""
        # 1. Extract context from incoming headers (case-insensitive dictionary)
        carrier = {k.lower(): v for k, v in request.headers.items()}
        extracted_context = extract(carrier)

        span_name = f"{request.method} {request.url.path}"
        with self._tracer.start_as_current_span(span_name, context=extracted_context) as span:
            span_ctx = span.get_span_context()
            trace_id_hex = trace.format_trace_id(span_ctx.trace_id)
            span_id_hex = trace.format_span_id(span_ctx.span_id)

            response = await call_next(request)

            response.headers["X-Trace-ID"] = trace_id_hex
            response.headers["X-Span-ID"] = span_id_hex
            return response
