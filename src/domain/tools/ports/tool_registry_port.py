"""Driven port contract for Tool Definition catalog and tenant availability."""

from abc import ABC, abstractmethod

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.value_objects.tool_definition import ToolDefinition


class ToolRegistryPort(ABC):
    """Abstract port for querying and managing available tool definitions per tenant."""

    @abstractmethod
    def get_tool(self, name: str) -> ToolDefinition | None:
        """Retrieves a tool definition by name."""
        raise NotImplementedError

    @abstractmethod
    def list_tools(self, tenant_id: TenantId | None = None) -> list[ToolDefinition]:
        """Lists available tools, optionally filtered by tenant permissions."""
        raise NotImplementedError

    @abstractmethod
    def is_tool_allowed(self, tenant_id: TenantId, tool_name: str) -> bool:
        """Checks if a tenant is authorized to execute a specific tool."""
        raise NotImplementedError
