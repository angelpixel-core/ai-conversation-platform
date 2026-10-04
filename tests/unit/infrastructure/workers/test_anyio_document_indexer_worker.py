"""Unit tests for AnyioDocumentIndexerWorker (Phase 4 RED)."""

from collections.abc import Sequence

import pytest

from src.domain.knowledge.entities.document import Document, DocumentStatus
from src.domain.knowledge.exceptions import DocumentNotFoundError
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.shared.events.event_envelope import EventEnvelope
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.embeddings.fake_embedding_client import (
    FakeEmbeddingClientAdapter,
)
from src.infrastructure.messaging.rabbitmq.anyio_document_indexer_worker import (
    AnyioDocumentIndexerWorker,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


class FailingEmbeddingClient(EmbeddingClientPort):
    """Failing embedding client simulating model provider outage."""

    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        raise RuntimeError("Embedding provider 503 service unavailable")


@pytest.fixture
def uow() -> InMemoryUnitOfWorkAdapter:
    return InMemoryUnitOfWorkAdapter()


def test_split_text_into_chunks_logic() -> None:
    worker = AnyioDocumentIndexerWorker(
        unit_of_work=InMemoryUnitOfWorkAdapter(),
        embedding_client=FakeEmbeddingClientAdapter(dimension=4),
        chunk_size=20,
        chunk_overlap=5,
    )
    text = "012345678901234567890123456789"  # length 30
    chunks = worker.split_text_into_chunks(text, chunk_size=20, chunk_overlap=5)

    assert len(chunks) == 2
    assert chunks[0] == "01234567890123456789"
    assert chunks[1] == "567890123456789"


@pytest.mark.anyio
async def test_worker_indexes_document_success(uow: InMemoryUnitOfWorkAdapter) -> None:
    tenant_id = TenantId("tenant-acme")
    document_id = "doc-99"

    # Seed pending document
    with uow:
        doc = Document.create(
            document_id=document_id,
            tenant_id=tenant_id,
            filename="handbook.txt",
            content_type="text/plain",
        )
        uow.knowledge.save_document(doc)
        uow.commit()

    embedding_client = FakeEmbeddingClientAdapter(dimension=8)
    worker = AnyioDocumentIndexerWorker(
        unit_of_work=uow,
        embedding_client=embedding_client,
        chunk_size=30,
        chunk_overlap=10,
        concurrency_limit=2,
    )

    long_content = (
        "Clean Architecture creates robust systems. "
        "Domain-driven design isolates business invariants. "
        "CQRS separates queries from state changes."
    )

    envelope = EventEnvelope(
        event_type="knowledge.document.uploaded",
        payload={
            "tenant_id": str(tenant_id),
            "document_id": document_id,
            "filename": "handbook.txt",
            "content": long_content,
        },
    )

    indexed_count = await worker.process_document_event(envelope)
    assert indexed_count > 1

    # Verify document is indexed in repository
    with uow:
        updated_doc = uow.knowledge.get_document(tenant_id, document_id)
        assert updated_doc is not None
        assert updated_doc.status == DocumentStatus.INDEXED
        assert updated_doc.total_chunks == indexed_count

        saved_chunks = uow.knowledge.get_chunks_by_document(tenant_id, document_id)
        assert len(saved_chunks) == indexed_count
        assert saved_chunks[0].embedding.dimensions == 8


@pytest.mark.anyio
async def test_worker_fails_gracefully_when_embedding_fails(uow: InMemoryUnitOfWorkAdapter) -> None:
    tenant_id = TenantId("tenant-acme")
    document_id = "doc-fail"

    with uow:
        doc = Document.create(
            document_id=document_id,
            tenant_id=tenant_id,
            filename="error.txt",
        )
        uow.knowledge.save_document(doc)
        uow.commit()

    worker = AnyioDocumentIndexerWorker(
        unit_of_work=uow,
        embedding_client=FailingEmbeddingClient(),
    )

    envelope = EventEnvelope(
        event_type="knowledge.document.uploaded",
        payload={
            "tenant_id": str(tenant_id),
            "document_id": document_id,
            "filename": "error.txt",
            "content": "Some text content to index.",
        },
    )

    with pytest.raises(RuntimeError, match="Embedding provider 503"):
        await worker.process_document_event(envelope)

    # Document should be marked as FAILED in repository
    with uow:
        updated_doc = uow.knowledge.get_document(tenant_id, document_id)
        assert updated_doc is not None
        assert updated_doc.status == DocumentStatus.FAILED


@pytest.mark.anyio
async def test_worker_raises_for_missing_document(uow: InMemoryUnitOfWorkAdapter) -> None:
    worker = AnyioDocumentIndexerWorker(
        unit_of_work=uow,
        embedding_client=FakeEmbeddingClientAdapter(dimension=4),
    )

    envelope = EventEnvelope(
        event_type="knowledge.document.uploaded",
        payload={
            "tenant_id": "tenant-unknown",
            "document_id": "doc-nonexistent",
            "filename": "test.txt",
            "content": "Sample content",
        },
    )

    with pytest.raises(DocumentNotFoundError):
        await worker.process_document_event(envelope)
