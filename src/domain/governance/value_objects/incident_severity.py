"""IncidentSeverity Enum Value Object."""

from enum import StrEnum


class IncidentSeverity(StrEnum):
    """Categorization of security incident severity."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
