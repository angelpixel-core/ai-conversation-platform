"""Relational Tenant repository adapter for Microsoft SQL Server."""

from sqlmodel import Session, select

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import TenantModel
from src.infrastructure.persistence.mssql.tenant_mapper import TenantMapper


class MssqlTenantRepositoryAdapter(TenantRepositoryPort):
    """Relational persistence adapter for tenants backed by Microsoft SQL Server."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, tenant: Tenant) -> None:
        """Persist or update a tenant and its policy."""
        model = TenantMapper.to_model(tenant)
        self._session.merge(model)
        self._session.flush()

    def get(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve a tenant by its ID without acquiring locks."""
        statement = select(TenantModel).where(TenantModel.id == str(tenant_id))
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return TenantMapper.to_domain(model)

    def get_for_update(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve a tenant acquiring a pessimistic row lock in MSSQL (UPDLOCK, ROWLOCK)."""
        statement = select(TenantModel).where(TenantModel.id == str(tenant_id)).with_for_update()
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return TenantMapper.to_domain(model)

    def list(self) -> list[Tenant]:
        """List all tenants registered in the platform."""
        statement = select(TenantModel)
        models = self._session.exec(statement).all()
        return [TenantMapper.to_domain(m) for m in models]


__all__ = ["MssqlTenantRepositoryAdapter"]
