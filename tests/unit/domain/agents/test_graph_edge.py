"""Unit tests for GraphEdge Value Object."""

import pytest

from src.domain.agents.value_objects.graph_edge import GraphEdge


def test_graph_edge_valid_creation() -> None:
    edge = GraphEdge(
        source_node="supervisor",
        target_node="researcher",
        condition_expression="state.get('needs_research') is True",
    )
    assert edge.source_node == "supervisor"
    assert edge.target_node == "researcher"
    assert edge.condition_expression == "state.get('needs_research') is True"


def test_graph_edge_default_condition_is_none() -> None:
    edge = GraphEdge(source_node="node_a", target_node="node_b")
    assert edge.condition_expression is None


def test_graph_edge_empty_source_raises_error() -> None:
    with pytest.raises(ValueError, match="source_node"):
        GraphEdge(source_node="   ", target_node="researcher")


def test_graph_edge_empty_target_raises_error() -> None:
    with pytest.raises(ValueError, match="target_node"):
        GraphEdge(source_node="supervisor", target_node="")
