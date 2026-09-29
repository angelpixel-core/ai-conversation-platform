"""Unit tests for WorkflowGraph Domain Entity."""

import pytest

from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.exceptions import GraphCycleDetectedError, InvalidGraphTransitionError
from src.domain.agents.value_objects.agent_role import AgentRole


def test_workflow_graph_valid_construction() -> None:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_node("researcher", AgentRole.SPECIALIST)
    graph.add_node("summarizer", AgentRole.SUMMARIZER)

    graph.add_edge("supervisor", "researcher")
    graph.add_edge("researcher", "summarizer")
    graph.add_edge("summarizer", "end")

    assert graph.entry_node == "supervisor"
    assert "end" in graph.end_nodes
    assert graph.get_next_nodes("supervisor") == ["researcher"]
    assert graph.get_next_nodes("researcher") == ["summarizer"]
    assert graph.get_next_nodes("summarizer") == ["end"]


def test_workflow_graph_empty_entry_node_raises_error() -> None:
    with pytest.raises(ValueError, match="entry_node"):
        WorkflowGraph(entry_node="   ")


def test_workflow_graph_empty_node_id_raises_error() -> None:
    graph = WorkflowGraph(entry_node="supervisor")
    with pytest.raises(ValueError, match="node_id"):
        graph.add_node("  ", AgentRole.SPECIALIST)


def test_workflow_graph_edge_with_unregistered_source_raises_error() -> None:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("researcher", AgentRole.SPECIALIST)
    with pytest.raises(InvalidGraphTransitionError, match="origen"):
        graph.add_edge("unregistered_source", "researcher")


def test_workflow_graph_edge_with_unregistered_target_raises_error() -> None:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    with pytest.raises(InvalidGraphTransitionError, match="destino"):
        graph.add_edge("supervisor", "unregistered_target")


def test_workflow_graph_cycle_detection_raises_error() -> None:
    graph = WorkflowGraph(entry_node="node_a", end_nodes={"end"})
    graph.add_node("node_a", AgentRole.SUPERVISOR)
    graph.add_node("node_b", AgentRole.SPECIALIST)
    graph.add_node("node_c", AgentRole.CRITIC)

    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", "node_c")
    graph.add_edge("node_c", "node_a")  # Cycle!

    with pytest.raises(GraphCycleDetectedError, match="Ciclo detectado"):
        graph.validate_dag()
