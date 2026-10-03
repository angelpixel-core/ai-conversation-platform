"""Enterprise AI Governance and Security Auditing HTTP Router."""

from fastapi import APIRouter, Query, status

from src.application.governance.queries.get_governance_metrics import (
    GetGovernanceMetricsQuery,
    GetGovernanceMetricsQueryHandler,
)
from src.application.governance.queries.list_incidents import (
    ListIncidentsQuery,
    ListIncidentsQueryHandler,
)
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.interfaces.http.governance_schemas import (
    GovernanceMetricsResponse,
    IncidentResponse,
)


def create_governance_router(incident_repo: IncidentRepositoryPort) -> APIRouter:
    """Factory creating APIRouter for Enterprise Governance, Auditing, and Safety Metrics."""
    router = APIRouter(prefix="/admin", tags=["Governance"])

    @router.get(
        "/tenants/{tenant_id}/incidents",
        response_model=list[IncidentResponse],
        status_code=status.HTTP_200_OK,
        summary="List tenant security incidents",
        description=(
            "Retrieves audit-grade security policy violations and guardrail incidents for a tenant."
        ),
    )
    async def list_tenant_incidents(
        tenant_id: str,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> list[IncidentResponse]:
        handler = ListIncidentsQueryHandler(incident_repo)
        incidents = await handler.handle(
            ListIncidentsQuery(tenant_id=tenant_id, limit=limit, offset=offset)
        )
        return [
            IncidentResponse(
                id=inc.id,
                tenant_id=str(inc.tenant_id),
                severity=str(inc.severity),
                rule_name=inc.rule_name,
                description=inc.description,
                prompt_preview=inc.prompt_preview,
                details=inc.details,
                created_at=inc.created_at,
            )
            for inc in incidents
        ]

    @router.get(
        "/governance/metrics",
        response_model=GovernanceMetricsResponse,
        status_code=status.HTTP_200_OK,
        summary="Get governance safety metrics",
        description=(
            "Retrieves aggregate security metrics and incident breakdowns across all tenants "
            "or filtered by tenant."
        ),
    )
    async def get_governance_metrics(
        tenant_id: str | None = Query(None),
    ) -> GovernanceMetricsResponse:
        handler = GetGovernanceMetricsQueryHandler(incident_repo)
        data = await handler.handle(GetGovernanceMetricsQuery(tenant_id=tenant_id))
        return GovernanceMetricsResponse(
            total_incidents=data.get("total_incidents", 0),
            by_severity=data.get("by_severity", {}),
            by_rule=data.get("by_rule", {}),
        )

    return router
