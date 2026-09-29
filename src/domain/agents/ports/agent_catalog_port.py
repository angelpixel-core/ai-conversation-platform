"""AgentCatalogPort Driven Port."""

from abc import ABC, abstractmethod

from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.tenants.value_objects.tenant_id import TenantId


class AgentCatalogPort(ABC):
    """Port for querying agent capabilities, roles and tenant-level configurations."""

    @abstractmethod
    def register_agent(self, agent_name: str, role: AgentRole) -> None:
        """Registers an agent into the catalog."""
        pass

    @abstractmethod
    def get_agent_role(self, agent_name: str) -> AgentRole | None:
        """Retrieves the assigned role of an agent."""
        pass

    @abstractmethod
    def list_available_agents(self, tenant_id: TenantId) -> list[str]:
        """Lists names of all agents enabled for a specific tenant."""
        pass
