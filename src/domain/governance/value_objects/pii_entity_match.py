"""PiiEntityMatch Value Object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PiiEntityMatch:
    """Immutable representation of a detected sensitive PII entity."""

    entity_type: str
    start_idx: int
    end_idx: int
    masked_value: str
    original_preview: str

    def __post_init__(self) -> None:
        if self.start_idx < 0:
            raise ValueError("El start_idx debe ser mayor o igual a 0.")

        if self.end_idx <= self.start_idx:
            raise ValueError("El end_idx debe ser estrictamente mayor que start_idx.")

        if not self.entity_type or not self.entity_type.strip():
            raise ValueError("El entity_type no puede estar vacío.")

        if not self.masked_value or not self.masked_value.strip():
            raise ValueError("El masked_value no puede estar vacío.")

    @property
    def span(self) -> tuple[int, int]:
        """Returns the character slice span (start_idx, end_idx)."""
        return (self.start_idx, self.end_idx)
