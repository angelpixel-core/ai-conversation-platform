"""MSSQL Knowledge repository adapter implementing hybrid search over document chunks."""

from collections.abc import Sequence

from sqlmodel import Session, select

from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.knowledge_mapper import KnowledgeDataMapper
from src.infrastructure.persistence.mssql.models import DocumentChunkModel, DocumentModel


class MssqlKnowledgeRepository(KnowledgeRepositoryPort):
    """SQLModel-backed repository for knowledge documents with hybrid vector retrieval."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_document(self, document: Document) -> None:
        """Persists or updates a knowledge document aggregate."""
        model = KnowledgeDataMapper.to_model_document(document)
        self._session.merge(model)

    def get_document(self, tenant_id: TenantId, document_id: str) -> Document | None:
        """Retrieves a document by tenant_id and document_id. Returns None if not found."""
        statement = select(DocumentModel).where(
            DocumentModel.tenant_id == str(tenant_id),
            DocumentModel.id == document_id,
        )
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return KnowledgeDataMapper.to_domain_document(model)

    def save_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        """Persists a batch of document chunks with their vector embeddings."""
        for chunk in chunks:
            model = KnowledgeDataMapper.to_model_chunk(chunk)
            self._session.merge(model)

    def get_chunks_by_document(self, tenant_id: TenantId, document_id: str) -> list[DocumentChunk]:
        """Retrieves all chunks for a given document within a tenant ordered by sequence number."""
        statement = (
            select(DocumentChunkModel)
            .where(
                DocumentChunkModel.tenant_id == str(tenant_id),
                DocumentChunkModel.document_id == document_id,
            )
            .order_by(DocumentChunkModel.sequence_number)  # pyright: ignore[reportArgumentType]
        )
        models = self._session.exec(statement).all()
        return [KnowledgeDataMapper.to_domain_chunk(m) for m in models]

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
        statement = select(DocumentChunkModel).where(DocumentChunkModel.tenant_id == str(tenant_id))
        chunk_models = self._session.exec(statement).all()
        if not chunk_models:
            return []

        tokens = set(query_text.lower().split())
        results: list[tuple[DocumentChunk, float]] = []

        for model in chunk_models:
            chunk = KnowledgeDataMapper.to_domain_chunk(model)
            v_score = query_vector.cosine_similarity(chunk.embedding)
            content_lower = chunk.content.lower()
            matches = sum(1 for t in tokens if t in content_lower)
            l_score = matches / len(tokens) if tokens else 0.0

            hybrid_score = (alpha * v_score) + ((1.0 - alpha) * l_score)
            if hybrid_score >= min_score:
                results.append((chunk, hybrid_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# Canonical adapter alias conforming to <Technology><Port>Adapter
MssqlKnowledgeRepositoryAdapter = MssqlKnowledgeRepository
