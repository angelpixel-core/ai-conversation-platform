"""Unit tests for DocumentChunk Entity."""

import pytest
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_document_chunk_creation() -> None:
    tenant_id = TenantId("tenant-acme")
    embedding = EmbeddingVector.from_list([0.6, 0.8])
    chunk = DocumentChunk(
        chunk_id="chk-1",
        document_id="doc-100",
        tenant_id=tenant_id,
        sequence_number=0,
        content="Antigravity architecture and clean domain design.",
        embedding=embedding,
        page_number=1,
    )

    assert chunk.id == "chk-1"
    assert chunk.document_id == "doc-100"
    assert chunk.tenant_id == tenant_id
    assert chunk.sequence_number == 0
    assert chunk.content == "Antigravity architecture and clean domain design."
    assert chunk.embedding == embedding
    assert chunk.page_number == 1
    assert chunk.created_at is not None


@pytest.mark.parametrize(
    ("chunk_id", "document_id", "seq", "content", "error_match"),
    [
        ("", "doc-1", 0, "text", "chunk_id"),
        ("chk-1", "", 0, "text", "document_id"),
        ("chk-1", "doc-1", -1, "text", "sequence_number"),
        ("chk-1", "doc-1", 0, "   ", "contenido"),
    ],
)
def test_document_chunk_invalid_inputs_raise_value_error(
    chunk_id: str,
    document_id: str,
    seq: int,
    content: str,
    error_match: str,
) -> None:
    embedding = EmbeddingVector.from_list([1.0, 0.0])
    with pytest.raises(ValueError, match=error_match):
        DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            tenant_id=TenantId("tenant-acme"),
            sequence_number=seq,
            content=content,
            embedding=embedding,
        )
