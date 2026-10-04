"""Unit tests for KnowledgeMapper."""

from src.domain.knowledge.entities.document import Document, DocumentStatus
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.knowledge_mapper import KnowledgeMapper


def test_mapper_document_roundtrip() -> None:
    tenant_id = TenantId("corp-acme")
    original = Document.create(
        document_id="doc-xyz",
        tenant_id=tenant_id,
        filename="handbook.pdf",
        content_type="application/pdf",
    )
    original.mark_processing()
    original.mark_indexed(total_chunks=5)

    model = KnowledgeMapper.to_model_document(original)
    assert model.id == "doc-xyz"
    assert model.tenant_id == "corp-acme"
    assert model.filename == "handbook.pdf"
    assert model.content_type == "application/pdf"
    assert model.status == "INDEXED"
    assert model.total_chunks == 5

    domain_doc = KnowledgeMapper.to_domain_document(model)
    assert domain_doc.id == "doc-xyz"
    assert domain_doc.tenant_id == tenant_id
    assert domain_doc.filename == "handbook.pdf"
    assert domain_doc.status == DocumentStatus.INDEXED
    assert domain_doc.total_chunks == 5


def test_mapper_chunk_roundtrip() -> None:
    tenant_id = TenantId("corp-acme")
    vector = EmbeddingVector.from_list([0.6, 0.8])
    chunk = DocumentChunk(
        chunk_id="chk-456",
        document_id="doc-xyz",
        tenant_id=tenant_id,
        sequence_number=1,
        content="Passage on DDD aggregate invariants.",
        embedding=vector,
        page_number=3,
    )

    model = KnowledgeMapper.to_model_chunk(chunk)
    assert model.id == "chk-456"
    assert model.tenant_id == "corp-acme"
    assert model.document_id == "doc-xyz"
    assert model.sequence_number == 1
    assert model.content == "Passage on DDD aggregate invariants."
    assert model.page_number == 3
    assert "[0.6" in model.embedding_json

    domain_chunk = KnowledgeMapper.to_domain_chunk(model)
    assert domain_chunk.id == "chk-456"
    assert domain_chunk.document_id == "doc-xyz"
    assert domain_chunk.tenant_id == tenant_id
    assert domain_chunk.sequence_number == 1
    assert domain_chunk.content == "Passage on DDD aggregate invariants."
    assert domain_chunk.page_number == 3
    assert domain_chunk.embedding.dimensions == 2
    assert domain_chunk.embedding.values[0] == chunk.embedding.values[0]
