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

    def __str__(self) -> str:
        return self.value
