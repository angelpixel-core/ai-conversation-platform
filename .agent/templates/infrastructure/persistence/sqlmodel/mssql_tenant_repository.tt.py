"""Template canónico para MssqlTenantRepository (Infraestructura / MSSQL).

Reglas:
- Pertenece a src/infrastructure/persistence/mssql/tenant_repository.py.
- Implementa TenantRepositoryPort.
- En 'get_for_update()', aplica bloqueo pesimista de fila en Microsoft SQL Server (.with_for_update() / UPDLOCK, ROWLOCK).
- Utiliza TenantDataMapper para desacoplar el dominio del modelo físico.
"""

from typing import List, Optional

from sqlmodel import Session, select

from src.domain.tenants.entities.tenant_entity import Tenant
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId
from .tenant_mapper import TenantDataMapper
from .tenant_model import TenantModel


class MssqlTenantRepository(TenantRepositoryPort):
    """Adaptador de persistencia relacional para inquilinos sobre Microsoft SQL Server."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, tenant: Tenant) -> None:
        """Persiste o actualiza un inquilino."""
        model = TenantDataMapper.to_model(tenant)
        self._session.merge(model)
        self._session.flush()

    def get(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Obtiene un inquilino por su ID sin adquirir bloqueos exclusivos."""
        statement = select(TenantModel).where(TenantModel.id == str(tenant_id))
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return TenantDataMapper.to_domain(model)

    def get_for_update(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Obtiene un inquilino adquiriendo bloqueo pesimista en MSSQL (UPDLOCK, ROWLOCK)."""
        statement = (
            select(TenantModel)
            .where(TenantModel.id == str(tenant_id))
            .with_for_update()
        )
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return TenantDataMapper.to_domain(model)

    def list(self) -> List[Tenant]:
        """Lista todos los inquilinos en el sistema."""
        statement = select(TenantModel)
        models = self._session.exec(statement).all()
        return [TenantDataMapper.to_domain(m) for m in models]
