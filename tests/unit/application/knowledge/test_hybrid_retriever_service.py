"""Unit tests for HybridRetrieverService."""

from collections.abc import Sequence
import pytest
from src.application.knowledge.services.hybrid_retriever_service import HybridRetrieverService
from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeEmbeddingClient(EmbeddingClientPort):
    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        return [EmbeddingVector.from_list([1.0, 0.0]) for _ in texts]


class FakeKnowledgeRepository(KnowledgeRepositoryPort):
    def __init__(self) -> None:
        self.doc = Document.create("doc-1", TenantId("t-1"), "guide.pdf")
        self.chunk = DocumentChunk(
            chunk_id="chk-1",
            document_id="doc-1",
            tenant_id=TenantId("t-1"),
            sequence_number=0,
            content="Antigravity clean architecture instructions.",
            embedding=EmbeddingVector.from_list([1.0, 0.0]),
            page_number=3,
        )

    def save_document(self, document: Document) -> None:
        pass

    def get_document(self, tenant_id: TenantId, document_id: str) -> Document | None:
        if tenant_id == TenantId("t-1") and document_id == "doc-1":
            return self.doc
        return None

    def save_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        pass

    def get_chunks_by_document(self, tenant_id: TenantId, document_id: str) -> list[DocumentChunk]:
        return [self.chunk] if tenant_id == TenantId("t-1") else []

    def search_hybrid(
        self,
        tenant_id: TenantId,
        query_text: str,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        min_score: float = 0.5,
        alpha: float = 0.7,
    ) -> list[tuple[DocumentChunk, float]]:
        if tenant_id == TenantId("t-1"):
            return [(self.chunk, 0.88)]
        return []


@pytest.mark.anyio
async def test_hybrid_retriever_empty_query_returns_empty() -> None:
    service = HybridRetrieverService(FakeEmbeddingClient(), FakeKnowledgeRepository())
    citations = await service.retrieve_context(TenantId("t-1"), "   ")
    assert citations == []


@pytest.mark.anyio
async def test_hybrid_retriever_returns_citations_for_tenant() -> None:
    service = HybridRetrieverService(FakeEmbeddingClient(), FakeKnowledgeRepository())
    citations = await service.retrieve_context(TenantId("t-1"), "clean architecture")

    assert len(citations) == 1
    cit = citations[0]
    assert cit.source_document_id == "doc-1"
    assert cit.document_name == "guide.pdf"
    assert cit.chunk_id == "chk-1"
    assert cit.page_number == 3
    assert cit.similarity_score == 0.88
    assert "Antigravity clean architecture" in cit.snippet


@pytest.mark.anyio
async def test_hybrid_retriever_other_tenant_returns_no_citations() -> None:
    service = HybridRetrieverService(FakeEmbeddingClient(), FakeKnowledgeRepository())
    citations = await service.retrieve_context(TenantId("t-other"), "clean architecture")
    assert citations == []
