"""GraphEdge Value Object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphEdge:
    """Represents a directed transition between two nodes in a State Graph."""

    source_node: str
    target_node: str
    condition_expression: str | None = None

    def __post_init__(self) -> None:
        if not self.source_node.strip():
            raise ValueError("El source_node no puede estar vacío.")
        if not self.target_node.strip():
            raise ValueError("El target_node no puede estar vacío.")
