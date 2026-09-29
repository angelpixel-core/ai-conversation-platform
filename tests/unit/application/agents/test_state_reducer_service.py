"""Unit tests for StateReducerService."""

import pytest

from src.application.agents.services.state_reducer_service import StateReducerService


def test_state_reducer_shallow_merge() -> None:
    reducer = StateReducerService()
    base_state = {"goal": "Audit contract", "status": "init"}
    updates = [
        {"research_summary": "Found 3 clauses", "status": "researched"},
        {"compliance_score": 95},
    ]

    result = reducer.reduce(base_state, updates)

    assert result["goal"] == "Audit contract"
    assert result["research_summary"] == "Found 3 clauses"
    assert result["compliance_score"] == 95
    assert result["status"] == "researched"


def test_state_reducer_concatenates_lists() -> None:
    reducer = StateReducerService()
    base_state = {"findings": ["initial_item"]}
    updates = [
        {"findings": ["clause_a", "clause_b"]},
        {"findings": ["clause_c"]},
    ]

    result = reducer.reduce(base_state, updates)

    assert result["findings"] == ["initial_item", "clause_a", "clause_b", "clause_c"]


def test_state_reducer_namespaced_mode() -> None:
    reducer = StateReducerService()
    base_state = {"workflow": "audit"}
    agent_updates = {
        "researcher": {"output": "SLA is compliant"},
        "critic": {"output": "Missing penalty section"},
    }

    result = reducer.reduce_namespaced(base_state, agent_updates)

    assert result["workflow"] == "audit"
    assert result["agent_outputs"]["researcher"]["output"] == "SLA is compliant"
    assert result["agent_outputs"]["critic"]["output"] == "Missing penalty section"
