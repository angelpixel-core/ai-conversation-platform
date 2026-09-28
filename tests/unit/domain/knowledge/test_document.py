"""Unit tests for Document Aggregate Root."""

import pytest

from src.domain.knowledge.entities.document import Document, DocumentStatus
from src.domain.knowledge.events.knowledge_events import (
    DocumentIndexedDomainEvent,
    DocumentUploadedDomainEvent,
)
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_document_creation_lifecycle() -> None:
    tenant_id = TenantId("corp-acme")
    doc = Document.create(
        document_id="doc-1",
        tenant_id=tenant_id,
        filename="manual.pdf",
        content_type="application/pdf",
    )

    assert doc.id == "doc-1"
    assert doc.tenant_id == tenant_id
    assert doc.filename == "manual.pdf"
    assert doc.content_type == "application/pdf"
    assert doc.status == DocumentStatus.PENDING
    assert doc.total_chunks == 0
    assert len(doc.domain_events) == 1
    assert isinstance(doc.domain_events[0], DocumentUploadedDomainEvent)

    # Process and Index
    doc.mark_processing()
    assert doc.status == DocumentStatus.PROCESSING

    doc.mark_indexed(total_chunks=8)
    assert doc.status == DocumentStatus.INDEXED
    assert doc.total_chunks == 8
    assert len(doc.domain_events) == 2
    assert isinstance(doc.domain_events[1], DocumentIndexedDomainEvent)


def test_document_mark_failed() -> None:
    doc = Document.create(
        document_id="doc-1",
        tenant_id=TenantId("corp-acme"),
        filename="manual.pdf",
    )
    doc.mark_processing()
    doc.mark_failed()
    assert doc.status == DocumentStatus.FAILED


def test_document_empty_filename_raises_value_error() -> None:
    with pytest.raises(ValueError, match="vacío"):
        Document.create(
            document_id="doc-1",
            tenant_id=TenantId("corp-acme"),
            filename="   ",
        )


def test_document_mark_indexed_invalid_chunk_count_raises_value_error() -> None:
    doc = Document.create(
        document_id="doc-1",
        tenant_id=TenantId("corp-acme"),
        filename="manual.pdf",
    )
    with pytest.raises(ValueError, match="mayor a cero"):
        doc.mark_indexed(total_chunks=0)
