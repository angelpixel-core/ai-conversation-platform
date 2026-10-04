"""WorkflowId and CheckpointId value objects."""

from dataclasses import dataclass

from src.domain.agents.value_objects.checkpoint_id import CheckpointId


@dataclass(frozen=True)
class WorkflowId:
    """Strongly typed identifier for a workflow instance."""

    value: str

    def __post_init__(self) -> None:
        clean = self.value.strip() if self.value else ""
        if not clean:
            raise ValueError("El workflow_id no puede estar vacío.")
        object.__setattr__(self, "value", clean)

    @classmethod
    def from_raw(cls, raw: str) -> "WorkflowId":
        """Semantic factory method creating WorkflowId from raw string."""
        return cls(value=raw)

    @classmethod
    def create(cls, value: str) -> "WorkflowId":
        """Semantic factory method creating WorkflowId."""
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


__all__ = ["CheckpointId", "WorkflowId"]
