"""Domain events for AI Governance and Observability."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class SafetyViolationBlockedDomainEvent:
    """Emitted when a safety guardrail blocks a malicious or disallowed request."""

    incident_id: str
    tenant_id: str
    rule_name: str
    severity: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PromptInjectionDetectedDomainEvent:
    """Emitted when an adversarial prompt injection or jailbreak attempt is detected."""

    incident_id: str
    tenant_id: str
    prompt_hash: str
    risk_score: float
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PiiRedactionAppliedDomainEvent:
    """Emitted when sensitive personal data (PII) is masked or redacted from input."""

    tenant_id: str
    redacted_count: int
    entity_types: list[str]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
