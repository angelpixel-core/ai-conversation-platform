"""SafetyVerdict Value Object."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SafetyVerdict:
    """Immutable result of evaluating content against safety guardrails."""

    is_safe: bool
    violation_type: str | None = None
    risk_score: float = 0.0
    matched_rule: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.risk_score <= 1.0):
            raise ValueError("El risk_score debe estar entre 0.0 y 1.0.")

        if self.is_safe and self.violation_type is not None:
            raise ValueError("Un veredicto seguro no puede contener violation_type.")

        if not self.is_safe and not self.violation_type:
            raise ValueError("Un veredicto inseguro debe especificar violation_type.")

    @classmethod
    def safe(cls, details: dict[str, Any] | None = None) -> "SafetyVerdict":
        """Factory for a safe evaluation verdict."""
        return cls(
            is_safe=True,
            violation_type=None,
            risk_score=0.0,
            matched_rule=None,
            details=details or {},
        )

    @classmethod
    def violation(
        cls,
        violation_type: str,
        risk_score: float,
        matched_rule: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "SafetyVerdict":
        """Factory for an unsafe violation verdict."""
        return cls(
            is_safe=False,
            violation_type=violation_type,
            risk_score=risk_score,
            matched_rule=matched_rule,
            details=details or {},
        )
