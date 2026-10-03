"""RecordSecurityIncidentCommand and Handler."""

import secrets
from dataclasses import dataclass, field
from typing import Any

from src.application.shared.ports.event_publisher import EventPublisher
from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class RecordSecurityIncidentCommand:
    """Command to record an audit-grade security incident."""

    tenant_id: str
    rule_name: str
    severity: str
    description: str
    prompt_preview: str
    details: dict[str, Any] = field(default_factory=dict)


class RecordSecurityIncidentHandler:
    """Handler executing the persistence and domain event publishing of security incidents."""

    def __init__(
        self,
        incident_repo: IncidentRepositoryPort,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._incident_repo = incident_repo
        self._event_publisher = event_publisher

    async def handle(self, command: RecordSecurityIncidentCommand) -> str:
        """Creates and persists an incident, publishing its domain events."""
        incident_id = f"inc-{secrets.token_hex(6)}"
        tenant_id = TenantId(command.tenant_id)
        severity = IncidentSeverity(command.severity.upper())

        incident = SecurityIncident.create(
            incident_id=incident_id,
            tenant_id=tenant_id,
            severity=severity,
            rule_name=command.rule_name,
            description=command.description,
            prompt_preview=command.prompt_preview,
            details=command.details,
        )

        await self._incident_repo.save_incident(incident)

        if self._event_publisher:
            for event in incident.pull_events():
                self._event_publisher.publish(event)

        return incident.id
