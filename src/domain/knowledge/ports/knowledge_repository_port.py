"""Driven port contract for Knowledge repository persistence and hybrid retrieval."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


class KnowledgeRepositoryPort(ABC):
    """Driven port for persistence and hybrid retrieval of documents and vector chunks."""

    @abstractmethod
    def save_document(self, document: Document) -> None:
        """Persists or updates a knowledge document aggregate."""
        raise NotImplementedError

    @abstractmethod
    def get_document(self, tenant_id: TenantId, document_id: str) -> Document | None:
        """Retrieves a document by tenant_id and document_id. Returns None if not found."""
        raise NotImplementedError

    @abstractmethod
    def save_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        """Persists a batch of document chunks with their vector embeddings."""
        raise NotImplementedError

    @abstractmethod
    def get_chunks_by_document(self, tenant_id: TenantId, document_id: str) -> list[DocumentChunk]:
        """Retrieves all chunks for a given document within a tenant."""
        raise NotImplementedError

    @abstractmethod
    def search_hybrid(
        self,
        tenant_id: TenantId,
        query_text: str,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        min_score: float = 0.5,
        alpha: float = 0.7,
    ) -> list[tuple[DocumentChunk, float]]:
        """Executes a hybrid search (lexical + vector) scoped to tenant_id."""
        raise NotImplementedError
