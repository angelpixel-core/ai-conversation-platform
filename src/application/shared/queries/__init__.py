"""Application shared queries."""

from src.application.shared.queries.get_health_status import (
    GetHealthStatusQuery,
    GetHealthStatusQueryHandler,
    HealthStatusResult,
)

__all__ = [
    "GetHealthStatusQuery",
    "GetHealthStatusQueryHandler",
    "HealthStatusResult",
]
