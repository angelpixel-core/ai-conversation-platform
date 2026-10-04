"""GovernanceMapper for translating between SecurityIncident and SecurityIncidentModel."""

import json

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import SecurityIncidentModel


class GovernanceMapper:
    """Translates between DDD SecurityIncident aggregate and physical SQLModel relational model."""

    @staticmethod
    def to_model(domain: SecurityIncident) -> SecurityIncidentModel:
        """Converts domain SecurityIncident aggregate root to SQLModel table model."""
        return SecurityIncidentModel(
            id=domain.id,
            tenant_id=domain.tenant_id.value,
            severity=str(domain.severity),
            rule_name=domain.rule_name,
            description=domain.description,
            prompt_preview=domain.prompt_preview,
            details_json=json.dumps(domain.details),
            created_at=domain.created_at,
        )

    @staticmethod
    def to_domain(model: SecurityIncidentModel) -> SecurityIncident:
        """Reconstructs domain SecurityIncident aggregate root from SQLModel table model."""
        details = json.loads(model.details_json) if model.details_json else {}
        return SecurityIncident(
            incident_id=model.id,
            tenant_id=TenantId(model.tenant_id),
            severity=IncidentSeverity(model.severity),
            rule_name=model.rule_name,
            description=model.description,
            prompt_preview=model.prompt_preview,
            details=details,
            created_at=model.created_at,
        )

    # Canonical alias conforming to to_persistence standard
    to_persistence = to_model


__all__ = ["GovernanceMapper"]
