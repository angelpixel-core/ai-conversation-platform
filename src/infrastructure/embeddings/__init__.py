"""Embedding client adapters for vector embedding generation."""

from src.infrastructure.embeddings.fake_embedding_client import FakeEmbeddingClientAdapter
from src.infrastructure.embeddings.httpx_embedding_client import HttpxEmbeddingClientAdapter

__all__ = ["FakeEmbeddingClientAdapter", "HttpxEmbeddingClientAdapter"]
