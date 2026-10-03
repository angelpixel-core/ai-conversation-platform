"""ListIncidentsQuery and Handler."""

from dataclasses import dataclass

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class ListIncidentsQuery:
    """Query to list security incidents scoped to a tenant."""

    tenant_id: str
    limit: int = 50
    offset: int = 0


class ListIncidentsQueryHandler:
    """Handler retrieving security incidents with pagination and tenant isolation."""

    def __init__(self, incident_repo: IncidentRepositoryPort) -> None:
        self._incident_repo = incident_repo

    async def handle(self, query: ListIncidentsQuery) -> list[SecurityIncident]:
        """Executes tenant-isolated retrieval of incidents."""
        tenant_id = TenantId(query.tenant_id)
        return await self._incident_repo.list_incidents_by_tenant(
            tenant_id=tenant_id,
            limit=query.limit,
            offset=query.offset,
        )
