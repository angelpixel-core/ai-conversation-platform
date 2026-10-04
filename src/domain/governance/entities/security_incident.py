"""SecurityIncident Aggregate Root."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from src.domain.governance.events.governance_events import (
    PromptInjectionDetectedDomainEvent,
    SafetyViolationBlockedDomainEvent,
)
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.value_objects.tenant_id import TenantId


class SecurityIncident(AggregateRoot):
    """Aggregate Root representing an audit-grade security or policy violation incident."""

    def __init__(
        self,
        incident_id: str,
        tenant_id: TenantId,
        severity: IncidentSeverity,
        rule_name: str,
        description: str,
        prompt_preview: str,
        details: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        """Initialize a SecurityIncident aggregate.

        Args:
            incident_id: Unique string identifier for the incident.
            tenant_id: TenantId owning or associated with the violation.
            severity: Categorical severity (LOW, MEDIUM, HIGH, CRITICAL).
            rule_name: Identifier of the triggered safety or governance rule.
            description: Narrative summary of the incident.
            prompt_preview: Redacted or truncated preview of triggering input.
            details: Optional dictionary of forensic metadata and risk scores.
            created_at: Optional UTC occurrence timestamp. Defaults to now.

        Raises:
            ValueError: If incident_id, rule_name, or prompt_preview is empty.
        """
        super().__init__()
        clean_id = incident_id.strip() if incident_id else ""
        if not clean_id:
            raise ValueError("El incident_id no puede estar vacío.")

        clean_rule = rule_name.strip() if rule_name else ""
        if not clean_rule:
            raise ValueError("El rule_name no puede estar vacío.")

        clean_prompt = prompt_preview.strip() if prompt_preview else ""
        if not clean_prompt:
            raise ValueError("El prompt_preview no puede estar vacío.")

        self._id = clean_id
        self._tenant_id = tenant_id
        self._severity = severity
        self._rule_name = clean_rule
        self._description = description.strip() if description else ""
        self._prompt_preview = clean_prompt
        self._details: dict[str, Any] = dict(details) if details else {}
        self._created_at = created_at or datetime.now(UTC)

    @property
    def id(self) -> str:
        """str: Unique identifier of the incident."""
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        """TenantId: Tenant identifier associated with the incident."""
        return self._tenant_id

    @property
    def severity(self) -> IncidentSeverity:
        """IncidentSeverity: Severity classification of the incident."""
        return self._severity

    @property
    def rule_name(self) -> str:
        """str: Name of the security/safety rule that triggered."""
        return self._rule_name

    @property
    def description(self) -> str:
        """str: Human-readable explanation of the violation."""
        return self._description

    @property
    def prompt_preview(self) -> str:
        """str: Sanitized preview snippet of the offending prompt."""
        return self._prompt_preview

    @property
    def details(self) -> dict[str, Any]:
        """dict[str, Any]: Supplemental diagnostic metadata dictionary."""
        return self._details

    @property
    def created_at(self) -> datetime:
        """datetime: Creation timestamp of the incident."""
        return self._created_at

    @classmethod
    def create(
        cls,
        incident_id: str,
        tenant_id: TenantId,
        severity: IncidentSeverity,
        rule_name: str,
        description: str,
        prompt_preview: str,
        details: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> "SecurityIncident":
        """Factory creating a security incident and recording associated domain events.

        Args:
            incident_id: Unique incident identifier.
            tenant_id: TenantId owning the incident.
            severity: IncidentSeverity classification.
            rule_name: Security rule name that matched.
            description: Narrative description.
            prompt_preview: Redacted prompt content snippet.
            details: Supplemental audit metadata. Defaults to None.
            created_at: Optional occurrence timestamp.

        Returns:
            Newly created SecurityIncident with SafetyViolationBlockedDomainEvent.
        """
        incident = cls(
            incident_id=incident_id,
            tenant_id=tenant_id,
            severity=severity,
            rule_name=rule_name,
            description=description,
            prompt_preview=prompt_preview,
            details=details,
            created_at=created_at,
        )

        # 1. Always record the safety violation blocked event
        incident.record_event(
            SafetyViolationBlockedDomainEvent(
                incident_id=incident.id,
                tenant_id=str(incident.tenant_id),
                rule_name=incident.rule_name,
                severity=str(incident.severity),
                occurred_at=incident.created_at,
            )
        )

        # 2. If severity is HIGH or CRITICAL, record prompt injection event
        if incident.severity in (IncidentSeverity.HIGH, IncidentSeverity.CRITICAL):
            prompt_hash = (
                incident.details.get("prompt_hash")
                or hashlib.sha256(incident.prompt_preview.encode("utf-8")).hexdigest()
            )
            risk_score = float(incident.details.get("risk_score", 1.0))
            incident.record_event(
                PromptInjectionDetectedDomainEvent(
                    incident_id=incident.id,
                    tenant_id=str(incident.tenant_id),
                    prompt_hash=prompt_hash,
                    risk_score=risk_score,
                    occurred_at=incident.created_at,
                )
            )

        return incident


__all__ = ["SecurityIncident"]
