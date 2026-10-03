"""Telemetry Infrastructure package."""

from src.infrastructure.telemetry.opentelemetry_config import (
    get_tracer,
    setup_opentelemetry,
)

__all__ = [
    "get_tracer",
    "setup_opentelemetry",
]
