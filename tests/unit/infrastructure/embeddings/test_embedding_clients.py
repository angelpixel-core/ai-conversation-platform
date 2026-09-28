"""Unit tests for embedding client adapters."""

import httpx
import pytest

from src.infrastructure.embeddings.fake_embedding_client import (
    FakeEmbeddingClientAdapter,
)
from src.infrastructure.embeddings.httpx_embedding_client import (
    HttpxEmbeddingClientAdapter,
)


@pytest.mark.anyio
async def test_fake_embedding_client_adapter() -> None:
    client = FakeEmbeddingClientAdapter(dimension=4)
    vectors = await client.generate_embeddings(["first text", "second passage"])

    assert len(vectors) == 2
    assert vectors[0].dimensions == 4
    assert vectors[1].dimensions == 4
    # Vectors must be normalized
    assert pytest.approx(vectors[0].cosine_similarity(vectors[0])) == 1.0


@pytest.mark.anyio
async def test_httpx_embedding_client_adapter_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {"embedding": [0.6, 0.8], "index": 0},
                    {"embedding": [1.0, 0.0], "index": 1},
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://api.openai.com"
    ) as http_client:
        client = HttpxEmbeddingClientAdapter(
            http_client=http_client,
            model_name="text-embedding-3-small",
        )
        vectors = await client.generate_embeddings(["hello", "world"])

        assert len(vectors) == 2
        assert vectors[0].dimensions == 2
        assert vectors[0].values == (0.6, 0.8)
        assert vectors[1].values == (1.0, 0.0)
