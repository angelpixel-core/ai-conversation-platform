"""Domain exceptions for AI Governance and Observability."""

from src.domain.shared.domain_error import DomainError


class SafetyPolicyViolationError(DomainError):
    """Raised when user prompt or model response violates an enterprise safety policy."""

    def __init__(
        self,
        message: str,
        violation_type: str,
        risk_score: float,
        matched_rule: str | None = None,
        incident_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.violation_type = violation_type
        self.risk_score = risk_score
        self.matched_rule = matched_rule
        self.incident_id = incident_id


class PiiMaskingError(DomainError):
    """Raised when an error occurs during PII scanning or redaction."""

    pass


class IncidentNotFoundError(DomainError):
    """Raised when a requested security incident is not found."""

    pass
