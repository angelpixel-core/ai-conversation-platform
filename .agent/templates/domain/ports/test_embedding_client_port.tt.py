"""Canonical test template: EmbeddingClientPort contract verification."""

from typing import Sequence

import pytest
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


class FakeEmbeddingClient(EmbeddingClientPort):
    """In-memory fake implementation of EmbeddingClientPort for contract testing."""

    def __init__(self, dimension: int = 4) -> None:
        self._dimension = dimension

    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        results: list[EmbeddingVector] = []
        for text in texts:
            # Deterministic mock embedding based on character count
            val = float(len(text) % 10 + 1)
            raw = [val] * self._dimension
            results.append(EmbeddingVector.from_list(raw))
        return results


@pytest.mark.anyio
async def test_embedding_client_contract() -> None:
    client = FakeEmbeddingClient(dimension=4)
    texts = ["hello world", "rag vector search"]

    vectors = await client.generate_embeddings(texts)

    assert len(vectors) == 2
    assert all(isinstance(v, EmbeddingVector) for v in vectors)
    assert vectors[0].dimension == 4
    # Ensure vectors are normalized
    assert abs(sum(x * x for x in vectors[0].values) - 1.0) < 1e-4
