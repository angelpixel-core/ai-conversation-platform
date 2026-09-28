"""Canonical test template: Knowledge Domain Events."""

from datetime import UTC, datetime

import pytest
from src.domain.knowledge.events.knowledge_events import (
    DocumentIndexedDomainEvent,
    DocumentIndexingFailedDomainEvent,
    DocumentUploadedDomainEvent,
    KnowledgeContextRetrievedDomainEvent,
)


def test_document_uploaded_domain_event() -> None:
    now = datetime.now(UTC)
    event = DocumentUploadedDomainEvent(
        document_id="doc-1",
        tenant_id="tenant-1",
        filename="handbook.pdf",
        content_type="application/pdf",
        occurred_at=now,
    )
    assert event.document_id == "doc-1"
    assert event.tenant_id == "tenant-1"
    assert event.filename == "handbook.pdf"
    assert event.content_type == "application/pdf"
    assert event.occurred_at == now

    with pytest.raises(AttributeError):
        event.filename = "new_name.pdf"  # type: ignore[misc]


def test_document_indexed_domain_event() -> None:
    now = datetime.now(UTC)
    event = DocumentIndexedDomainEvent(
        document_id="doc-1",
        tenant_id="tenant-1",
        total_chunks=12,
        occurred_at=now,
    )
    assert event.document_id == "doc-1"
    assert event.total_chunks == 12
    assert event.occurred_at == now


def test_document_indexing_failed_domain_event() -> None:
    now = datetime.now(UTC)
    event = DocumentIndexingFailedDomainEvent(
        document_id="doc-1",
        tenant_id="tenant-1",
        error_reason="Embedding model quota exceeded",
        occurred_at=now,
    )
    assert event.document_id == "doc-1"
    assert event.error_reason == "Embedding model quota exceeded"


def test_knowledge_context_retrieved_domain_event() -> None:
    now = datetime.now(UTC)
    event = KnowledgeContextRetrievedDomainEvent(
        tenant_id="tenant-1",
        conversation_id="conv-1",
        query="what is our policy?",
        retrieved_chunk_ids=["chk-1", "chk-2"],
        occurred_at=now,
    )
    assert event.tenant_id == "tenant-1"
    assert event.conversation_id == "conv-1"
    assert event.query == "what is our policy?"
    assert event.retrieved_chunk_ids == ["chk-1", "chk-2"]
