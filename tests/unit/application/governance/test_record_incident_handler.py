"""Unit tests for Governance CQRS Commands and Queries."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.governance.commands.record_incident import (
    RecordSecurityIncidentCommand,
    RecordSecurityIncidentHandler,
)
from src.application.governance.queries.get_governance_metrics import (
    GetGovernanceMetricsQuery,
    GetGovernanceMetricsQueryHandler,
)
from src.application.governance.queries.list_incidents import (
    ListIncidentsQuery,
    ListIncidentsQueryHandler,
)
from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.tenants.value_objects.tenant_id import TenantId


@pytest.fixture
def mock_incident_repo() -> Mock:
    mock = Mock(spec=IncidentRepositoryPort)
    mock.save_incident = AsyncMock()
    mock.list_incidents_by_tenant = AsyncMock(return_value=[])
    mock.get_metrics = AsyncMock(return_value={"total_incidents": 5, "critical_count": 2})
    return mock


@pytest.mark.anyio
async def test_record_incident_command_handler(mock_incident_repo: Mock) -> None:
    handler = RecordSecurityIncidentHandler(incident_repo=mock_incident_repo)
    command = RecordSecurityIncidentCommand(
        tenant_id="corp-acme",
        rule_name="PROMPT_INJECTION_RULE",
        severity="HIGH",
        description="Jailbreak detected",
        prompt_preview="Ignore previous instructions",
        details={"risk_score": 0.88},
    )

    incident_id = await handler.handle(command)

    assert incident_id.startswith("inc-")
    mock_incident_repo.save_incident.assert_awaited_once()
    saved = mock_incident_repo.save_incident.call_args[0][0]
    assert saved.id == incident_id
    assert saved.tenant_id == TenantId("corp-acme")
    assert saved.severity == IncidentSeverity.HIGH


@pytest.mark.anyio
async def test_record_incident_command_handler_with_event_publisher(
    mock_incident_repo: Mock,
) -> None:
    mock_publisher = Mock()
    handler = RecordSecurityIncidentHandler(
        incident_repo=mock_incident_repo,
        event_publisher=mock_publisher,
    )
    command = RecordSecurityIncidentCommand(
        tenant_id="corp-acme",
        rule_name="PROMPT_INJECTION_RULE",
        severity="CRITICAL",
        description="Prompt injection detected",
        prompt_preview="Ignore instructions",
    )

    incident_id = await handler.handle(command)

    assert incident_id.startswith("inc-")
    assert mock_publisher.publish.call_count == 2


@pytest.mark.anyio
async def test_list_incidents_query_handler(mock_incident_repo: Mock) -> None:
    tenant_id = TenantId("corp-acme")
    sample_incident = SecurityIncident.create(
        incident_id="inc-1",
        tenant_id=tenant_id,
        severity=IncidentSeverity.LOW,
        rule_name="PII_WARN",
        description="desc",
        prompt_preview="preview",
    )
    mock_incident_repo.list_incidents_by_tenant = AsyncMock(return_value=[sample_incident])

    handler = ListIncidentsQueryHandler(incident_repo=mock_incident_repo)
    query = ListIncidentsQuery(tenant_id="corp-acme", limit=10, offset=0)

    results = await handler.handle(query)

    assert len(results) == 1
    assert results[0].id == "inc-1"
    mock_incident_repo.list_incidents_by_tenant.assert_awaited_once_with(
        tenant_id=tenant_id, limit=10, offset=0
    )


@pytest.mark.anyio
async def test_get_governance_metrics_query_handler(mock_incident_repo: Mock) -> None:
    handler = GetGovernanceMetricsQueryHandler(incident_repo=mock_incident_repo)
    query = GetGovernanceMetricsQuery(tenant_id="corp-acme")

    metrics = await handler.handle(query)

    assert metrics["total_incidents"] == 5
    assert metrics["critical_count"] == 2
    mock_incident_repo.get_metrics.assert_awaited_once_with(tenant_id=TenantId("corp-acme"))
