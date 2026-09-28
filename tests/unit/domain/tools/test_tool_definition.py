"""Unit tests for ToolDefinition Value Object."""

import pytest
from src.domain.tools.value_objects.tool_definition import ToolDefinition


def test_tool_definition_valid_creation() -> None:
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
        is_deterministic=True,
        requires_approval=True,
    )
    assert tool.name == "refund_order"
    assert "Processes a financial refund" in tool.description
    assert tool.is_deterministic is True
    assert tool.requires_approval is True
    assert tool.parameters_schema["required"] == ["order_id", "amount"]


def test_tool_definition_defaults() -> None:
    tool = ToolDefinition(
        name="get_weather",
        description="Fetches current weather for a city",
        parameters_schema={"type": "object"},
    )
    assert tool.is_deterministic is True
    assert tool.requires_approval is False


def test_tool_definition_empty_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="nombre"):
        ToolDefinition(
            name="   ",
            description="Valid description",
            parameters_schema={},
        )


def test_tool_definition_empty_description_raises_value_error() -> None:
    with pytest.raises(ValueError, match="descripción"):
        ToolDefinition(
            name="valid_tool",
            description="",
            parameters_schema={},
        )


def test_tool_definition_invalid_schema_type_raises_value_error() -> None:
    with pytest.raises(ValueError, match="parameters_schema"):
        ToolDefinition(
            name="valid_tool",
            description="Valid description",
            parameters_schema="not a dict",  # type: ignore[arg-type]
        )


def test_tool_definition_immutability() -> None:
    tool = ToolDefinition(
        name="valid_tool",
        description="Valid description",
        parameters_schema={},
    )
    with pytest.raises(AttributeError):
        tool.name = "new_name"  # type: ignore[misc]
