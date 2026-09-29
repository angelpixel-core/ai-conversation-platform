"""Canonical template: WorkflowGraph Domain Entity."""

from typing import Any

from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.agents.value_objects.graph_edge import GraphEdge


class WorkflowGraph:
    """Represents a declarative Directed Acyclic Graph (DAG) for multi-agent workflows."""

    def __init__(self, entry_node: str, end_nodes: set[str] | None = None) -> None:
        if not entry_node.strip():
            raise ValueError("El entry_node no puede estar vacío.")
        self.entry_node = entry_node
        self.end_nodes = end_nodes or set()
        self.nodes: dict[str, AgentRole] = {}
        self.edges: list[GraphEdge] = []

    def add_node(self, node_id: str, role: AgentRole) -> None:
        """Registers a node with its assigned agent role."""
        if not node_id.strip():
            raise ValueError("El node_id no puede estar vacío.")
        self.nodes[node_id] = role

    def add_edge(self, source: str, target: str, condition: str | None = None) -> None:
        """Adds a directed transition between two nodes."""
        if source not in self.nodes:
            raise ValueError(f"Nodo de origen '{source}' no registrado en el grafo.")
        if target not in self.nodes and target not in self.end_nodes:
            raise ValueError(f"Nodo de destino '{target}' no registrado en el grafo.")
        self.edges.append(GraphEdge(source_node=source, target_node=target, condition_expression=condition))

    def get_next_nodes(self, current_node: str, state_data: dict[str, Any] | None = None) -> list[str]:
        """Returns the next candidate nodes from current_node."""
        return [edge.target_node for edge in self.edges if edge.source_node == current_node]
