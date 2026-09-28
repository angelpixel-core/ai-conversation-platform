"""Canonical test template: ToolPolicyEvaluatorService."""

from decimal import Decimal
from src.application.tools.services.tool_policy_evaluator_service import ToolPolicyEvaluatorService
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition


def test_evaluator_requires_approval_when_tool_flagged() -> None:
    evaluator = ToolPolicyEvaluatorService()
    tenant = Tenant(
        tenant_id=TenantId("corp-acme"),
        name="Acme Corp",
        budget=MonetaryBudget(allocated_usd=Decimal("100.00")),
    )
    tool = ToolDefinition(name="refund", description="desc", parameters_schema={}, requires_approval=True)
    call = ToolCall(call_id="c-1", tool_name="refund", arguments={})

    assert evaluator.requires_human_approval(tenant, tool, call) is True


def test_evaluator_allows_automatic_when_tool_not_flagged() -> None:
    evaluator = ToolPolicyEvaluatorService()
    tenant = Tenant(
        tenant_id=TenantId("corp-acme"),
        name="Acme Corp",
        budget=MonetaryBudget(allocated_usd=Decimal("100.00")),
    )
    tool = ToolDefinition(name="search_docs", description="desc", parameters_schema={}, requires_approval=False)
    call = ToolCall(call_id="c-1", tool_name="search_docs", arguments={})

    assert evaluator.requires_human_approval(tenant, tool, call) is False
