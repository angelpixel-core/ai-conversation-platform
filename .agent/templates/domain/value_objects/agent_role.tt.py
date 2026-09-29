"""Canonical template: AgentRole Value Object."""

from enum import StrEnum


class AgentRole(StrEnum):
    """Enumeration of agent specializations in a multi-agent workflow."""

    SUPERVISOR = "SUPERVISOR"
    SPECIALIST = "SPECIALIST"
    CRITIC = "CRITIC"
    SUMMARIZER = "SUMMARIZER"
