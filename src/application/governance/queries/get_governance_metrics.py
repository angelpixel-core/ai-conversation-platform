"""GetGovernanceMetricsQuery and Handler."""

from dataclasses import dataclass
from typing import Any

from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class GetGovernanceMetricsQuery:
    """Query to fetch aggregate governance and safety metrics."""

    tenant_id: str | None = None


class GetGovernanceMetricsQueryHandler:
    """Handler retrieving security governance metrics."""

    def __init__(self, incident_repo: IncidentRepositoryPort) -> None:
        """Initialize the governance metrics query handler.

        Args:
            incident_repo: Driven port for incident querying and metrics calculation.
        """
        self._incident_repo = incident_repo

    async def handle(self, query: GetGovernanceMetricsQuery) -> dict[str, Any]:
        """Execute retrieval of governance metrics optionally filtered by tenant.

        Args:
            query: GetGovernanceMetricsQuery optionally specifying a tenant filter.

        Returns:
            Dictionary containing total incident counts, severity, and rule breakdown.
        """
        tenant_id = TenantId(query.tenant_id) if query.tenant_id else None
        return await self._incident_repo.get_metrics(tenant_id=tenant_id)


__all__ = [
    "GetGovernanceMetricsQuery",
    "GetGovernanceMetricsQueryHandler",
]
