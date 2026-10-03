"""In-memory adapter for IncidentRepositoryPort."""

from typing import Any

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId


class InMemoryIncidentRepositoryAdapter(IncidentRepositoryPort):
    """Fast, in-memory repository for governance security incidents."""

    def __init__(self) -> None:
        self._incidents: dict[str, SecurityIncident] = {}

    async def save_incident(self, incident: SecurityIncident) -> None:
        """Stores the security incident in memory."""
        self._incidents[incident.id] = incident

    async def get_incident(self, tenant_id: TenantId, incident_id: str) -> SecurityIncident | None:
        """Retrieves an incident scoped to a specific tenant."""
        inc = self._incidents.get(incident_id)
        if inc is None or inc.tenant_id != tenant_id:
            return None
        return inc

    async def list_incidents_by_tenant(
        self, tenant_id: TenantId, limit: int = 50, offset: int = 0
    ) -> list[SecurityIncident]:
        """Lists incidents scoped to a tenant ordered descending by timestamp."""
        tenant_incidents = [inc for inc in self._incidents.values() if inc.tenant_id == tenant_id]
        tenant_incidents.sort(key=lambda x: x.created_at, reverse=True)
        return tenant_incidents[offset : offset + limit]

    async def get_metrics(self, tenant_id: TenantId | None = None) -> dict[str, Any]:
        """Calculates security governance metrics."""
        incidents = (
            [inc for inc in self._incidents.values() if inc.tenant_id == tenant_id]
            if tenant_id is not None
            else list(self._incidents.values())
        )

        by_severity: dict[str, int] = {}
        by_rule: dict[str, int] = {}

        for inc in incidents:
            sev_str = str(inc.severity)
            by_severity[sev_str] = by_severity.get(sev_str, 0) + 1
            by_rule[inc.rule_name] = by_rule.get(inc.rule_name, 0) + 1

        return {
            "total_incidents": len(incidents),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }
