"""SubAgentExecutorPort Driven Port."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.agents.value_objects.agent_role import AgentRole


class SubAgentExecutorPort(ABC):
    """Port for delegating node tasks to subagents or tool executors."""

    @abstractmethod
    async def execute_node(
        self,
        node_id: str,
        role: AgentRole,
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Executes a node with the given role and state, returning state delta/output."""
        pass
