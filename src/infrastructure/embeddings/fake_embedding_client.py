"""Fake embedding client adapter for fast testing without external network calls."""

from collections.abc import Sequence

from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


class FakeEmbeddingClientAdapter(EmbeddingClientPort):
    """Deterministic in-memory embedding generator producing normalized dense vectors."""

    def __init__(self, dimension: int = 1536) -> None:
        if dimension <= 0:
            raise ValueError("Dimension must be positive.")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Returns the configured vector dimensionality."""
        return self._dimension

    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        """Generates deterministic L2-normalized embeddings for a batch of texts."""
        embeddings: list[EmbeddingVector] = []
        for text in texts:
            # Deterministic pseudo-embedding based on text content and dimension index
            base_hash = abs(hash(text))
            values = [float(((base_hash + i * 31) % 97) + 1) for i in range(self._dimension)]
            embeddings.append(EmbeddingVector.from_list(values, normalize=True))
        return embeddings
