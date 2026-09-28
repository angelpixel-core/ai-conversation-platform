"""Unit tests for IndexDocumentChunksCommand and IndexDocumentChunksHandler."""

from collections.abc import Sequence
from typing import Self

import pytest

from src.application.knowledge.commands.index_document_chunks import (
    ChunkInput,
    IndexDocumentChunksCommand,
    IndexDocumentChunksHandler,
)
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.knowledge.entities.document import Document, DocumentStatus
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.exceptions import DocumentNotFoundError
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeEmbeddingClient(EmbeddingClientPort):
    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        return [EmbeddingVector.from_list([1.0, 0.0]) for _ in texts]


class FakeKnowledgeRepo(KnowledgeRepositoryPort):
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], Document] = {}
        self.chunks: list[DocumentChunk] = []

    def save_document(self, document: Document) -> None:
        self.documents[(str(document.tenant_id), str(document.id))] = document

    def get_document(self, tenant_id: TenantId, document_id: str) -> Document | None:
        return self.documents.get((str(tenant_id), document_id))

    def save_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        self.chunks.extend(chunks)

    def get_chunks_by_document(self, tenant_id: TenantId, document_id: str) -> list[DocumentChunk]:
        return [c for c in self.chunks if c.tenant_id == tenant_id and c.document_id == document_id]

    def search_hybrid(
        self,
        tenant_id: TenantId,
        query_text: str,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        min_score: float = 0.5,
        alpha: float = 0.7,
    ) -> list[tuple[DocumentChunk, float]]:
        return []


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.knowledge = FakeKnowledgeRepo()  # type: ignore[attr-defined]
        self.committed = False
        self.conversations = None  # type: ignore[assignment]
        self.tenants = None  # type: ignore[assignment]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


@pytest.mark.anyio
async def test_index_document_chunks_success() -> None:
    uow = FakeUnitOfWork()
    embedding_client = FakeEmbeddingClient()
    tid = TenantId("tenant-1")

    doc = Document.create("doc-1", tid, "handbook.pdf")
    uow.knowledge.save_document(doc)

    handler = IndexDocumentChunksHandler(
        unit_of_work=uow,
        embedding_client=embedding_client,
    )

    command = IndexDocumentChunksCommand(
        tenant_id="tenant-1",
        document_id="doc-1",
        chunks=[
            ChunkInput(content="Section 1: Architecture", page_number=1),
            ChunkInput(content="Section 2: Testing", page_number=2),
        ],
    )

    result = await handler.handle(command)

    assert result.document_id == "doc-1"
    assert result.total_chunks == 2
    assert result.status == DocumentStatus.INDEXED.value
    assert uow.committed is True

    updated_doc = uow.knowledge.get_document(tid, "doc-1")
    assert updated_doc is not None
    assert updated_doc.status == DocumentStatus.INDEXED
    assert updated_doc.total_chunks == 2

    stored_chunks = uow.knowledge.get_chunks_by_document(tid, "doc-1")
    assert len(stored_chunks) == 2
    assert stored_chunks[0].content == "Section 1: Architecture"
    assert stored_chunks[1].page_number == 2


@pytest.mark.anyio
async def test_index_document_chunks_document_not_found() -> None:
    uow = FakeUnitOfWork()
    handler = IndexDocumentChunksHandler(
        unit_of_work=uow,
        embedding_client=FakeEmbeddingClient(),
    )

    command = IndexDocumentChunksCommand(
        tenant_id="tenant-1",
        document_id="missing-doc",
        chunks=[ChunkInput(content="text", page_number=1)],
    )

    with pytest.raises(DocumentNotFoundError):
        await handler.handle(command)


@pytest.mark.anyio
async def test_index_document_chunks_empty_chunks_raises_error() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("tenant-1")
    doc = Document.create("doc-1", tid, "handbook.pdf")
    uow.knowledge.save_document(doc)

    handler = IndexDocumentChunksHandler(
        unit_of_work=uow,
        embedding_client=FakeEmbeddingClient(),
    )

    command = IndexDocumentChunksCommand(
        tenant_id="tenant-1",
        document_id="doc-1",
        chunks=[],
    )

    with pytest.raises(ValueError, match="vacía"):
        await handler.handle(command)


class FailingEmbeddingClient(EmbeddingClientPort):
    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        raise RuntimeError("Embedding service unavailable")


@pytest.mark.anyio
async def test_index_document_chunks_embedding_failure_marks_document_failed() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("tenant-1")
    doc = Document.create("doc-1", tid, "handbook.pdf")
    uow.knowledge.save_document(doc)

    handler = IndexDocumentChunksHandler(
        unit_of_work=uow,
        embedding_client=FailingEmbeddingClient(),
    )

    command = IndexDocumentChunksCommand(
        tenant_id="tenant-1",
        document_id="doc-1",
        chunks=[ChunkInput(content="Section 1", page_number=1)],
    )

    with pytest.raises(RuntimeError, match="Embedding service unavailable"):
        await handler.handle(command)

    updated_doc = uow.knowledge.get_document(tid, "doc-1")
    assert updated_doc is not None
    assert updated_doc.status == DocumentStatus.FAILED
