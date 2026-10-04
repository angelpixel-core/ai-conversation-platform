"""In-memory Knowledge repository adapter for unit and integration testing."""

from collections.abc import Sequence

from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


class InMemoryKnowledgeRepositoryAdapter(KnowledgeRepositoryPort):
    """Fast dictionary-backed repository for knowledge documents and vector chunks."""

    def __init__(self) -> None:
        self._documents: dict[tuple[str, str], Document] = {}
        self._chunks: list[DocumentChunk] = []

    def save_document(self, document: Document) -> None:
        self._documents[(str(document.tenant_id), str(document.id))] = document

    def get_document(self, tenant_id: TenantId, document_id: str) -> Document | None:
        return self._documents.get((str(tenant_id), document_id))

    def save_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        self._chunks.extend(chunks)

    def get_chunks_by_document(self, tenant_id: TenantId, document_id: str) -> list[DocumentChunk]:
        return [
            c for c in self._chunks if c.tenant_id == tenant_id and c.document_id == document_id
        ]

    def search_hybrid(
        self,
        tenant_id: TenantId,
        query_text: str,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        min_score: float = 0.5,
        alpha: float = 0.7,
    ) -> list[tuple[DocumentChunk, float]]:
        results: list[tuple[DocumentChunk, float]] = []
        tokens = set(query_text.lower().split())

        for chunk in self._chunks:
            if chunk.tenant_id != tenant_id:
                continue

            v_score = query_vector.cosine_similarity(chunk.embedding)
            content_lower = chunk.content.lower()
            matches = sum(1 for t in tokens if t in content_lower)
            l_score = matches / len(tokens) if tokens else 0.0

            hybrid_score = (alpha * v_score) + ((1.0 - alpha) * l_score)
            if hybrid_score >= min_score:
                results.append((chunk, hybrid_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


__all__ = ["InMemoryKnowledgeRepositoryAdapter"]
