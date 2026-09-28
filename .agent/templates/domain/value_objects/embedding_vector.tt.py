"""Canonical template: EmbeddingVector Value Object."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingVector:
    """Immutable representation of a normalized dense vector embedding."""

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("El vector de embedding no puede estar vacío.")
        for v in self.values:
            if math.isnan(v) or math.isinf(v):
                raise ValueError("Los valores del embedding deben ser números reales finitos.")

    @property
    def dimensions(self) -> int:
        """Returns the dimensionality of the embedding vector."""
        return len(self.values)

    @classmethod
    def from_list(cls, values: list[float], normalize: bool = True) -> "EmbeddingVector":
        """Factory creating a vector from a list of floats, optionally normalizing with L2 norm."""
        if not values:
            raise ValueError("La lista de valores no puede estar vacía.")
        if not normalize:
            return cls(values=tuple(values))

        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0.0:
            return cls(values=tuple(values))
        return cls(values=tuple(v / norm for v in values))

    def dot_product(self, other: "EmbeddingVector") -> float:
        """Calculates dot product against another vector of the same dimension."""
        if self.dimensions != other.dimensions:
            raise ValueError(
                f"Dimensiones incompatibles: {self.dimensions} vs {other.dimensions}."
            )
        return sum(a * b for a, b in zip(self.values, other.values, strict=True))

    def cosine_similarity(self, other: "EmbeddingVector") -> float:
        """Calculates cosine similarity (equivalent to dot product if normalized)."""
        dot = self.dot_product(other)
        norm_a = math.sqrt(sum(v * v for v in self.values))
        norm_b = math.sqrt(sum(v * v for v in other.values))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm_a * norm_b)))
