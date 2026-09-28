"""Driven port contract for generating dense vector embeddings from text."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


class EmbeddingClientPort(ABC):
    """Abstract driven port for embedding model providers."""

    @abstractmethod
    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        """Generates normalized vector embeddings for a given batch of text segments."""
        raise NotImplementedError
