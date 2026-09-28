"""ToolPolicyEvaluatorService evaluates execution policies and Human-in-the-Loop criteria."""

from src.domain.tenants.entities.tenant import Tenant
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition


class ToolPolicyEvaluatorService:
    """Evaluates whether a tool call can be executed automatically or requires
    human-in-the-loop (HITL) approval.
    """

    def requires_human_approval(
        self,
        tenant: Tenant,
        tool_definition: ToolDefinition,
        tool_call: ToolCall,
    ) -> bool:
        """Determines if the tool execution requires human approval."""
        if tool_definition.requires_approval:
            return True
        if not tenant.is_active:
            return True
        return False
