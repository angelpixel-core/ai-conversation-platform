"""GuardedCommandExecutor application service/decorator.

Intercepts commands, executes safety guardrails and PII redaction,
and persists security incidents when violations occur before mutating domain state.
"""

import secrets
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.application.governance.services.guardrail_pipeline_service import (
    SafetyGuardrailPipelineService,
)
from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.exceptions import SafetyPolicyViolationError
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.tenants.value_objects.tenant_id import TenantId

T = TypeVar("T")


class GuardedCommandExecutor:
    """Orchestrates guarded command execution with automated PII masking and incident logging."""

    def __init__(
        self,
        pipeline: SafetyGuardrailPipelineService,
        incident_repo: IncidentRepositoryPort,
    ) -> None:
        self._pipeline = pipeline
        self._incident_repo = incident_repo

    async def execute_guarded(
        self,
        tenant_id: TenantId,
        raw_text: str,
        operation: Callable[[str], Awaitable[T]],
    ) -> T:
        """Evaluates input through guardrail pipeline, redact PII and blocks safety violations."""
        result = await self._pipeline.evaluate_and_sanitize(raw_text, tenant_id=tenant_id)

        if not result.is_safe:
            incident_id = f"inc-{secrets.token_hex(6)}"
            severity = (
                IncidentSeverity.CRITICAL
                if result.verdict.risk_score >= 0.8
                else IncidentSeverity.HIGH
            )
            rule_name = result.verdict.matched_rule or "SAFETY_VIOLATION"
            description = str(
                result.verdict.details.get("description", "Safety guardrail policy violation")
            )
            prompt_preview = raw_text[:200]

            incident = SecurityIncident.create(
                incident_id=incident_id,
                tenant_id=tenant_id,
                severity=severity,
                rule_name=rule_name,
                description=description,
                prompt_preview=prompt_preview,
                details=result.verdict.details,
            )

            await self._incident_repo.save_incident(incident)

            raise SafetyPolicyViolationError(
                message=f"Prompt blocked by safety policy: {result.verdict.violation_type}",
                violation_type=result.verdict.violation_type or "SAFETY_VIOLATION",
                risk_score=result.verdict.risk_score,
                matched_rule=result.verdict.matched_rule,
                incident_id=incident.id,
            )

        return await operation(result.sanitized_text)
