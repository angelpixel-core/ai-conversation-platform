"""Unit tests for AgentRole Value Object."""

import pytest

from src.domain.agents.value_objects.agent_role import AgentRole


def test_agent_role_enumeration_values() -> None:
    assert AgentRole.SUPERVISOR == "SUPERVISOR"
    assert AgentRole.SPECIALIST == "SPECIALIST"
    assert AgentRole.CRITIC == "CRITIC"
    assert AgentRole.SUMMARIZER == "SUMMARIZER"


def test_agent_role_invalid_raises_error() -> None:
    with pytest.raises(ValueError):
        AgentRole("INVALID_ROLE")
