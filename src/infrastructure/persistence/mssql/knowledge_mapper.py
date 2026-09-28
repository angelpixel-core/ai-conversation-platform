"""Data mapper for converting between Knowledge domain entities and MSSQL models."""

from src.domain.knowledge.entities.document import Document, DocumentStatus
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import DocumentChunkModel, DocumentModel


class KnowledgeDataMapper:
    """Bi-directional mapper between Knowledge domain models and physical relational models."""

    @staticmethod
    def to_model_document(domain: Document) -> DocumentModel:
        """Converts a domain Document aggregate into its physical DocumentModel."""
        return DocumentModel(
            id=domain.id,
            tenant_id=str(domain.tenant_id),
            filename=domain.filename,
            content_type=domain.content_type,
            status=str(domain.status),
            total_chunks=domain.total_chunks,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    @staticmethod
    def to_domain_document(model: DocumentModel) -> Document:
        """Converts a physical DocumentModel into a reconstituted domain Document aggregate."""
        return Document(
            document_id=model.id,
            tenant_id=TenantId(model.tenant_id),
            filename=model.filename,
            content_type=model.content_type,
            status=DocumentStatus(model.status),
            total_chunks=model.total_chunks,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model_chunk(domain: DocumentChunk) -> DocumentChunkModel:
        """Converts a domain DocumentChunk entity into its physical DocumentChunkModel."""
        return DocumentChunkModel(
            id=domain.id,
            tenant_id=str(domain.tenant_id),
            document_id=domain.document_id,
            sequence_number=domain.sequence_number,
            content=domain.content,
            embedding_json=domain.embedding.to_json(),
            page_number=domain.page_number,
            created_at=domain.created_at,
        )

    @staticmethod
    def to_domain_chunk(model: DocumentChunkModel) -> DocumentChunk:
        """Converts a physical DocumentChunkModel into a domain DocumentChunk entity."""
        return DocumentChunk(
            chunk_id=model.id,
            document_id=model.document_id,
            tenant_id=TenantId(model.tenant_id),
            sequence_number=model.sequence_number,
            content=model.content,
            embedding=EmbeddingVector.from_json(model.embedding_json),
            page_number=model.page_number,
            created_at=model.created_at,
        )
