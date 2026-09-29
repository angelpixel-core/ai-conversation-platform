"""WorkflowGraph Domain Entity."""

from typing import Any

from src.domain.agents.exceptions import GraphCycleDetectedError, InvalidGraphTransitionError
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.agents.value_objects.graph_edge import GraphEdge


class WorkflowGraph:
    """Represents a declarative Directed Acyclic Graph (DAG) for multi-agent workflows."""

    def __init__(self, entry_node: str, end_nodes: set[str] | None = None) -> None:
        clean_entry = entry_node.strip() if entry_node else ""
        if not clean_entry:
            raise ValueError("El entry_node no puede estar vacío.")
        self.entry_node = clean_entry
        self.end_nodes = end_nodes or set()
        self.nodes: dict[str, AgentRole] = {}
        self.edges: list[GraphEdge] = []

    def add_node(self, node_id: str, role: AgentRole) -> None:
        """Registers a node with its assigned agent role."""
        clean_id = node_id.strip() if node_id else ""
        if not clean_id:
            raise ValueError("El node_id no puede estar vacío.")
        self.nodes[clean_id] = role

    def add_edge(self, source: str, target: str, condition: str | None = None) -> None:
        """Adds a directed transition between two nodes."""
        if source not in self.nodes:
            raise InvalidGraphTransitionError(
                f"Nodo de origen '{source}' no registrado en el grafo."
            )
        if target not in self.nodes and target not in self.end_nodes:
            raise InvalidGraphTransitionError(
                f"Nodo de destino '{target}' no registrado en el grafo."
            )
        self.edges.append(
            GraphEdge(source_node=source, target_node=target, condition_expression=condition)
        )

    def get_next_nodes(
        self, current_node: str, state_data: dict[str, Any] | None = None
    ) -> list[str]:
        """Returns the next candidate nodes from current_node."""
        return [edge.target_node for edge in self.edges if edge.source_node == current_node]

    def validate_dag(self) -> None:
        """Validates that the graph contains no cycles using depth-first search."""
        # Build adjacency list
        adj: dict[str, list[str]] = {node: [] for node in self.nodes}
        for node in self.end_nodes:
            if node not in adj:
                adj[node] = []
        for edge in self.edges:
            adj[edge.source_node].append(edge.target_node)

        # 0 = unvisited, 1 = visiting (in current recursion stack), 2 = visited
        visited: dict[str, int] = {node: 0 for node in adj}

        def _dfs(node: str) -> None:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited.get(neighbor) == 1:
                    raise GraphCycleDetectedError(
                        f"Ciclo detectado en el grafo entre '{node}' y '{neighbor}'."
                    )
                if visited.get(neighbor, 0) == 0:
                    _dfs(neighbor)
            visited[node] = 2

        for node in self.nodes:
            if visited[node] == 0:
                _dfs(node)
