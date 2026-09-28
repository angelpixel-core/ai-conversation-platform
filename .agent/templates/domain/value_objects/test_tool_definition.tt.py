"""Canonical test template: ToolDefinition Value Object."""

import pytest
from src.domain.tools.value_objects.tool_definition import ToolDefinition


def test_tool_definition_valid() -> None:
    tool = ToolDefinition(
        name="refund_order",
        description="Processes a financial refund for a previous order",
        parameters_schema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
            },
            "required": ["order_id", "amount"],
        },
        requires_approval=True,
    )
    assert tool.name == "refund_order"
    assert tool.requires_approval is True
    assert "order_id" in tool.parameters_schema["properties"]


def test_tool_definition_empty_name_raises_error() -> None:
    with pytest.raises(ValueError, match="nombre"):
        ToolDefinition(
            name="   ",
            description="some description",
            parameters_schema={},
        )
