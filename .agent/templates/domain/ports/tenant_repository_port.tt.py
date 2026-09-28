"""Template canónico para el Puerto de Repositorio de Inquilinos (TenantRepositoryPort).

Reglas:
- Pertenece a la capa de Dominio (Driven Port).
- Trabaja con el Value Object TenantId y el Aggregate Root Tenant.
- Provee 'get_for_update' para bloqueo pesimista en implementaciones relacionales (MSSQL).
- Totalmente agnóstico a la tecnología de persistencia.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.tenant_entity import Tenant
from ..value_objects.tenant_id import TenantId


class TenantRepositoryPort(ABC):
    """Contrato abstracto para la persistencia del agregado Tenant."""

    @abstractmethod
    def add(self, tenant: Tenant) -> None:
        """Persiste o actualiza un agregado Tenant."""
        raise NotImplementedError

    @abstractmethod
    def get(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Obtiene un tenant por su identificador. Retorna None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def get_for_update(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Obtiene un tenant adquiriendo un bloqueo pesimista de fila (UPDLOCK) para reserva de cuota."""
        raise NotImplementedError

    @abstractmethod
    def list(self) -> List[Tenant]:
        """Retorna todos los inquilinos registrados."""
        raise NotImplementedError
