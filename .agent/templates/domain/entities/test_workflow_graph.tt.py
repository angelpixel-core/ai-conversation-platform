"""Canonical test template: WorkflowGraph Domain Entity."""

import pytest

from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.value_objects.agent_role import AgentRole


def test_workflow_graph_construction() -> None:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_node("researcher", AgentRole.SPECIALIST)
    graph.add_edge("supervisor", "researcher")
    graph.add_edge("researcher", "end")

    assert graph.entry_node == "supervisor"
    assert "end" in graph.end_nodes
    assert graph.get_next_nodes("supervisor") == ["researcher"]
    assert graph.get_next_nodes("researcher") == ["end"]


def test_workflow_graph_unregistered_node_raises_error() -> None:
    graph = WorkflowGraph(entry_node="supervisor")
    with pytest.raises(ValueError, match="no registrado"):
        graph.add_edge("unregistered", "target")
