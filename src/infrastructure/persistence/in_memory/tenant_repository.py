"""In-memory Tenant repository adapter for fast unit and integration tests."""

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.tenant_id import TenantId


class InMemoryTenantRepositoryAdapter(TenantRepositoryPort):
    """Fast in-memory dictionary-backed repository for Tenant aggregate roots."""

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}

    def add(self, tenant: Tenant) -> None:
        """Persist or update tenant in memory."""
        self._tenants[str(tenant.id)] = tenant

    def get(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve tenant by identifier."""
        return self._tenants.get(str(tenant_id))

    def get_for_update(self, tenant_id: TenantId) -> Tenant | None:
        """Retrieve tenant (in-memory simulation of pessimistic locking)."""
        return self._tenants.get(str(tenant_id))

    def list(self) -> list[Tenant]:
        """List all tenants in memory."""
        return list(self._tenants.values())


# Backward compatible alias
InMemoryTenantRepository = InMemoryTenantRepositoryAdapter
