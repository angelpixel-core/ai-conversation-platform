"""Integration test: Governance admin endpoints for auditing incidents and metrics."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.in_memory_incident_repository import (
    InMemoryIncidentRepositoryAdapter,
)
from src.interfaces.http.api import build_api


@pytest.fixture
def client_and_incident_repo() -> tuple[AsyncClient, InMemoryIncidentRepositoryAdapter]:
    incident_repo = InMemoryIncidentRepositoryAdapter()
    app = build_api(
        incident_repo=incident_repo,
    )
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, incident_repo


@pytest.mark.anyio
async def test_get_incidents_by_tenant(
    client_and_incident_repo: tuple[AsyncClient, InMemoryIncidentRepositoryAdapter],
) -> None:
    client, repo = client_and_incident_repo
    tenant_id = TenantId("corp-acme")
    incident = SecurityIncident.create(
        incident_id="inc-admin-1",
        tenant_id=tenant_id,
        severity=IncidentSeverity.CRITICAL,
        rule_name="PROMPT_INJECTION",
        description="Jailbreak detected",
        prompt_preview="Ignore rules",
    )
    await repo.save_incident(incident)

    response = await client.get("/admin/tenants/corp-acme/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "inc-admin-1"
    assert data[0]["severity"] == "CRITICAL"
    assert data[0]["rule_name"] == "PROMPT_INJECTION"


@pytest.mark.anyio
async def test_get_governance_metrics(
    client_and_incident_repo: tuple[AsyncClient, InMemoryIncidentRepositoryAdapter],
) -> None:
    client, repo = client_and_incident_repo
    tenant_id = TenantId("corp-acme")
    incident = SecurityIncident.create(
        incident_id="inc-admin-2",
        tenant_id=tenant_id,
        severity=IncidentSeverity.HIGH,
        rule_name="PII_VIOLATION",
        description="PII leak",
        prompt_preview="SSN leak",
    )
    await repo.save_incident(incident)

    response = await client.get("/admin/governance/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["total_incidents"] == 1
    assert metrics["by_severity"]["HIGH"] == 1
