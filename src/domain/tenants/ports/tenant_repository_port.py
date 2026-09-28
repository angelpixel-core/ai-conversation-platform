"""Driven port contract for Tenant aggregate root persistence."""

from abc import ABC, abstractmethod

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.value_objects.tenant_id import TenantId


class TenantRepositoryPort(ABC):
    """Abstract persistence port for Tenant aggregate root."""

    @abstractmethod
    def add(self, tenant: Tenant) -> None:
        """Persists or updates a tenant aggregate."""
        raise NotImplementedError

    @abstractmethod
    def get(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieves a tenant by identifier. Returns None if not found."""
        raise NotImplementedError

    @abstractmethod
    def get_for_update(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieves a tenant with pessimistic row-level lock for atomic budget reservation."""
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[Tenant]:
        """Lists all registered tenants."""
        raise NotImplementedError
