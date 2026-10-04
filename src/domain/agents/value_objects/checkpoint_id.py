"""CheckpointId Value Object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckpointId:
    """Strongly typed identifier for a state snapshot checkpoint."""

    value: str

    def __post_init__(self) -> None:
        clean = self.value.strip() if self.value else ""
        if not clean:
            raise ValueError("El checkpoint_id no puede estar vacío.")
        object.__setattr__(self, "value", clean)

    @classmethod
    def from_raw(cls, raw: str) -> "CheckpointId":
        """Semantic factory method creating CheckpointId from raw string."""
        return cls(value=raw)

    @classmethod
    def create(cls, value: str) -> "CheckpointId":
        """Semantic factory method creating CheckpointId."""
        return cls(value=value)

    def __str__(self) -> str:
        return self.value
