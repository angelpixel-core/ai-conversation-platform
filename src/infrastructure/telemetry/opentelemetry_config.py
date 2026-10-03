"""OpenTelemetry configuration and initialization with resilient W3C propagation."""

from opentelemetry import trace
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def setup_opentelemetry(service_name: str = "chatbot-api") -> TracerProvider:
    """Configures the TracerProvider with W3C TraceContext propagator."""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    set_global_textmap(TraceContextTextMapPropagator())
    return provider


def get_tracer(instrumenting_module_name: str) -> Tracer:
    """Gets an OpenTelemetry tracer for the instrumented component."""
    return trace.get_tracer(instrumenting_module_name)
