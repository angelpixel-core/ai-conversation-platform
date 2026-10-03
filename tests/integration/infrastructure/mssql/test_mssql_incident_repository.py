"""Integration tests for MssqlIncidentRepository against live SQL Server."""

import pytest
from sqlalchemy.engine import Engine

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.connection import create_session_factory
from src.infrastructure.persistence.mssql.models import TenantModel
from src.infrastructure.persistence.mssql.mssql_incident_repository import (
    MssqlIncidentRepository,
)


@pytest.mark.anyio
async def test_mssql_incident_repository_integration_live_db(
    mssql_engine: Engine, clean_db: None
) -> None:
    session_factory = create_session_factory(mssql_engine)
    tenant_id = TenantId("corp-incident-test")

    with session_factory() as session:
        t = TenantModel(id=tenant_id.value, name="Live Incident Tenant")
        session.add(t)
        session.commit()

    incident = SecurityIncident.create(
        incident_id="inc-live-01",
        tenant_id=tenant_id,
        severity=IncidentSeverity.CRITICAL,
        rule_name="INTEGRATION_JAILBREAK",
        description="Jailbreak test against live DB",
        prompt_preview="Live SQL Server prompt preview",
        details={"engine": "mssql2022"},
    )

    with session_factory() as session:
        repo = MssqlIncidentRepository(session=session)
        await repo.save_incident(incident)

    with session_factory() as session:
        repo = MssqlIncidentRepository(session=session)
        retrieved = await repo.get_incident(tenant_id, "inc-live-01")
        assert retrieved is not None
        assert retrieved.id == "inc-live-01"
        assert retrieved.severity == IncidentSeverity.CRITICAL
        assert retrieved.details == {"engine": "mssql2022"}

        metrics = await repo.get_metrics(tenant_id)
        assert metrics["total_incidents"] == 1
        assert metrics["by_severity"]["CRITICAL"] == 1
