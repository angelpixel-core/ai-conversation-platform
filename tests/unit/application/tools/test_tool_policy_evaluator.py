"""Unit tests for ToolPolicyEvaluatorService."""

from decimal import Decimal

from src.application.tools.services.tool_policy_evaluator_service import (
    ToolPolicyEvaluatorService,
)
from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition


def _create_tenant(is_active: bool = True) -> Tenant:
    return Tenant(
        tenant_id=TenantId("corp-acme"),
        name="Acme Corp",
        budget=MonetaryBudget(balance=Decimal("100.00")),
        status=TenantStatus.ACTIVE if is_active else TenantStatus.SUSPENDED,
    )


def test_evaluator_requires_approval_when_tool_flagged() -> None:
    evaluator = ToolPolicyEvaluatorService()
    tenant = _create_tenant()
    tool = ToolDefinition(
        name="refund_order",
        description="Processes a financial refund",
        parameters_schema={"type": "object"},
        requires_approval=True,
    )
    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 50})

    assert evaluator.requires_human_approval(tenant, tool, call) is True


def test_evaluator_allows_automatic_when_tool_not_flagged() -> None:
    evaluator = ToolPolicyEvaluatorService()
    tenant = _create_tenant()
    tool = ToolDefinition(
        name="get_weather",
        description="Fetches current weather",
        parameters_schema={"type": "object"},
        requires_approval=False,
    )
    call = ToolCall(call_id="c-2", tool_name="get_weather", arguments={"city": "Santiago"})

    assert evaluator.requires_human_approval(tenant, tool, call) is False


def test_evaluator_requires_approval_when_tenant_inactive() -> None:
    evaluator = ToolPolicyEvaluatorService()
    tenant = _create_tenant(is_active=False)
    tool = ToolDefinition(
        name="get_weather",
        description="Fetches current weather",
        parameters_schema={"type": "object"},
        requires_approval=False,
    )
    call = ToolCall(call_id="c-3", tool_name="get_weather", arguments={})

    assert evaluator.requires_human_approval(tenant, tool, call) is True
