"""MSSQL Incident Repository adapter using SQLModel."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from sqlmodel import Session, col, select

from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.governance_mapper import GovernanceMapper
from src.infrastructure.persistence.mssql.models import SecurityIncidentModel


class MssqlIncidentRepository(IncidentRepositoryPort):
    """MSSQL 2022 persistent adapter for security incidents with atomic session isolation."""

    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session_or_factory = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        if callable(self._session_or_factory):
            with self._session_or_factory() as session:
                yield session
        else:
            yield self._session_or_factory

    async def save_incident(self, incident: SecurityIncident) -> None:
        """Persists an immutable security incident record atomically."""
        model = GovernanceMapper.to_model(incident)
        with self._get_session() as session:
            session.merge(model)
            session.commit()

    async def get_incident(self, tenant_id: TenantId, incident_id: str) -> SecurityIncident | None:
        """Retrieves a specific incident under tenant isolation."""
        stmt = select(SecurityIncidentModel).where(
            SecurityIncidentModel.tenant_id == tenant_id.value,
            SecurityIncidentModel.id == incident_id,
        )
        with self._get_session() as session:
            model = session.exec(stmt).first()
            if model is None:
                return None
            return GovernanceMapper.to_domain(model)

    async def list_incidents_by_tenant(
        self, tenant_id: TenantId, limit: int = 50, offset: int = 0
    ) -> list[SecurityIncident]:
        """Lists incidents scoped to a tenant ordered descending by timestamp."""
        stmt = (
            select(SecurityIncidentModel)
            .where(SecurityIncidentModel.tenant_id == tenant_id.value)
            .order_by(col(SecurityIncidentModel.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        with self._get_session() as session:
            models = session.exec(stmt).all()
            return [GovernanceMapper.to_domain(m) for m in models]

    async def get_metrics(self, tenant_id: TenantId | None = None) -> dict[str, Any]:
        """Calculates security governance metrics (counts, breakdown by severity, rule)."""
        stmt = select(SecurityIncidentModel)
        if tenant_id is not None:
            stmt = stmt.where(SecurityIncidentModel.tenant_id == tenant_id.value)

        with self._get_session() as session:
            models = session.exec(stmt).all()

        total = len(models)
        by_severity: dict[str, int] = {}
        by_rule: dict[str, int] = {}

        for m in models:
            by_severity[m.severity] = by_severity.get(m.severity, 0) + 1
            by_rule[m.rule_name] = by_rule.get(m.rule_name, 0) + 1

        return {
            "total_incidents": total,
            "by_severity": by_severity,
            "by_rule": by_rule,
        }


# Canonical adapter alias conforming to <Technology><Port>Adapter
MssqlIncidentRepositoryAdapter = MssqlIncidentRepository
