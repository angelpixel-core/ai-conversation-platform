"""Canonical template: EmbeddingClientPort (Driven Port).

Invariants:
- Belongs strictly to the Domain layer.
- Driven port abstraction for generating vector embeddings from text batches.
- Returns domain Value Objects (EmbeddingVector).
"""

from abc import ABC, abstractmethod
from typing import Sequence

from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


class EmbeddingClientPort(ABC):
    """Abstract driven port for embedding model providers."""

    @abstractmethod
    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        """Generates normalized vector embeddings for a given batch of text segments."""
        raise NotImplementedError
