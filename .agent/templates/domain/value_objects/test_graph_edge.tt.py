"""Canonical test template: GraphEdge Value Object."""

import pytest

from src.domain.agents.value_objects.graph_edge import GraphEdge


def test_graph_edge_valid() -> None:
    edge = GraphEdge(source_node="supervisor", target_node="researcher", condition_expression="needs_rag == True")
    assert edge.source_node == "supervisor"
    assert edge.target_node == "researcher"
    assert edge.condition_expression == "needs_rag == True"


def test_graph_edge_empty_source_raises_error() -> None:
    with pytest.raises(ValueError, match="source_node"):
        GraphEdge(source_node="", target_node="researcher")


def test_graph_edge_empty_target_raises_error() -> None:
    with pytest.raises(ValueError, match="target_node"):
        GraphEdge(source_node="supervisor", target_node="")
