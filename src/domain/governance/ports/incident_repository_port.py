"""IncidentRepositoryPort Driven Port."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.tenants.value_objects.tenant_id import TenantId


class IncidentRepositoryPort(ABC):
    """Port for transactional persistence, querying and metrics of security incidents."""

    @abstractmethod
    async def save_incident(self, incident: SecurityIncident) -> None:
        """Persists an immutable security incident record."""
        pass

    @abstractmethod
    async def get_incident(self, tenant_id: TenantId, incident_id: str) -> SecurityIncident | None:
        """Retrieves a specific incident under tenant isolation."""
        pass

    @abstractmethod
    async def list_incidents_by_tenant(
        self, tenant_id: TenantId, limit: int = 50, offset: int = 0
    ) -> list[SecurityIncident]:
        """Lists incidents scoped to a tenant ordered descending by timestamp."""
        pass

    @abstractmethod
    async def get_metrics(self, tenant_id: TenantId | None = None) -> dict[str, Any]:
        """Calculates security governance metrics (counts, breakdown by severity, rule)."""
        pass
