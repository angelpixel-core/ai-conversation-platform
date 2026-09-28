"""Unit tests for EmbeddingVector Value Object."""

import math

import pytest

from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


def test_embedding_vector_creation_and_normalization() -> None:
    raw = [3.0, 4.0]
    vec = EmbeddingVector.from_list(raw, normalize=True)

    assert vec.dimensions == 2
    assert pytest.approx(vec.values[0], rel=1e-4) == 0.6
    assert pytest.approx(vec.values[1], rel=1e-4) == 0.8
    # L2 norm must equal 1.0
    assert pytest.approx(math.sqrt(sum(x * x for x in vec.values)), rel=1e-4) == 1.0


def test_embedding_vector_from_list_without_normalization() -> None:
    raw = [3.0, 4.0]
    vec = EmbeddingVector.from_list(raw, normalize=False)

    assert vec.dimensions == 2
    assert vec.values == (3.0, 4.0)


def test_embedding_vector_empty_raises_value_error() -> None:
    with pytest.raises(ValueError, match="vacío|vacía"):
        EmbeddingVector.from_list([])

    with pytest.raises(ValueError, match="vacío|vacía"):
        EmbeddingVector(values=())


def test_embedding_vector_nan_or_inf_raises_value_error() -> None:
    with pytest.raises(ValueError, match="finitos"):
        EmbeddingVector.from_list([1.0, float("nan")])

    with pytest.raises(ValueError, match="finitos"):
        EmbeddingVector.from_list([1.0, float("inf")])


def test_embedding_vector_zero_vector_handled() -> None:
    vec = EmbeddingVector.from_list([0.0, 0.0], normalize=True)
    assert vec.values == (0.0, 0.0)


def test_embedding_vector_dot_product() -> None:
    v1 = EmbeddingVector.from_list([1.0, 2.0], normalize=False)
    v2 = EmbeddingVector.from_list([3.0, 4.0], normalize=False)

    assert pytest.approx(v1.dot_product(v2)) == 11.0


def test_embedding_vector_dot_product_dimension_mismatch() -> None:
    v1 = EmbeddingVector.from_list([1.0, 2.0])
    v2 = EmbeddingVector.from_list([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="incompatibles"):
        v1.dot_product(v2)


def test_embedding_vector_cosine_similarity() -> None:
    v1 = EmbeddingVector.from_list([1.0, 0.0])
    v2 = EmbeddingVector.from_list([1.0, 0.0])
    v3 = EmbeddingVector.from_list([0.0, 1.0])
    v4 = EmbeddingVector.from_list([-1.0, 0.0])

    assert pytest.approx(v1.cosine_similarity(v2), rel=1e-4) == 1.0
    assert pytest.approx(v1.cosine_similarity(v3), rel=1e-4) == 0.0
    assert pytest.approx(v1.cosine_similarity(v4), rel=1e-4) == -1.0


def test_embedding_vector_immutable() -> None:
    vec = EmbeddingVector.from_list([1.0, 2.0])
    with pytest.raises(AttributeError):
        vec.values = (3.0, 4.0)  # type: ignore[misc]
