"""HTTPX-based embedding client adapter for OpenAI-compatible embedding endpoints."""

from collections.abc import Sequence

import httpx

from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector


class HttpxEmbeddingClientAdapter(EmbeddingClientPort):
    """Embedding adapter querying an OpenAI-compatible HTTP embedding API."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        model_name: str = "text-embedding-3-small",
    ) -> None:
        self._http_client = http_client
        self._model_name = model_name

    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        """Generates normalized vector embeddings by calling the embeddings endpoint."""
        if not texts:
            return []

        response = await self._http_client.post(
            "/v1/embeddings",
            json={
                "input": list(texts),
                "model": self._model_name,
            },
        )
        response.raise_for_status()
        payload = response.json()
        raw_items = payload.get("data", [])
        sorted_items = sorted(raw_items, key=lambda item: item.get("index", 0))

        return [
            EmbeddingVector.from_list(item["embedding"], normalize=True) for item in sorted_items
        ]
