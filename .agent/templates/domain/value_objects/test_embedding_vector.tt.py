"""Canonical test template: EmbeddingVector Value Object."""

import pytest
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


def test_embedding_vector_creation_and_normalization() -> None:
    raw = [3.0, 4.0]
    vec = EmbeddingVector.from_list(raw, normalize=True)
    assert vec.dimensions == 2
    assert pytest.approx(vec.values[0], rel=1e-4) == 0.6
    assert pytest.approx(vec.values[1], rel=1e-4) == 0.8


def test_embedding_vector_empty_raises_value_error() -> None:
    with pytest.raises(ValueError, match="vacío"):
        EmbeddingVector.from_list([])


def test_embedding_vector_cosine_similarity() -> None:
    v1 = EmbeddingVector.from_list([1.0, 0.0])
    v2 = EmbeddingVector.from_list([1.0, 0.0])
    v3 = EmbeddingVector.from_list([0.0, 1.0])

    assert pytest.approx(v1.cosine_similarity(v2), rel=1e-4) == 1.0
    assert pytest.approx(v1.cosine_similarity(v3), rel=1e-4) == 0.0
