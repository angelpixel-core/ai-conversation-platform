"""Unit tests verifying contracts of Knowledge driven ports."""

from typing import Sequence

import pytest
from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeKnowledgeRepository(KnowledgeRepositoryPort):
    """In-memory implementation verifying KnowledgeRepositoryPort contract."""

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
        return [
            c for c in self.chunks
            if c.tenant_id == tenant_id and c.document_id == document_id
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

        for chunk in self.chunks:
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


class FakeEmbeddingClient(EmbeddingClientPort):
    """In-memory fake implementation of EmbeddingClientPort for contract testing."""

    def __init__(self, dimension: int = 4) -> None:
        self._dimension = dimension

    async def generate_embeddings(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        results: list[EmbeddingVector] = []
        for text in texts:
            val = float(len(text) % 10 + 1)
            raw = [val] * self._dimension
            results.append(EmbeddingVector.from_list(raw))
        return results


def test_knowledge_repository_contract() -> None:
    repo = FakeKnowledgeRepository()
    tenant_id = TenantId("acme")
    other_tenant = TenantId("other")

    doc = Document.create(
        document_id="doc-1",
        tenant_id=tenant_id,
        filename="specs.md",
    )
    repo.save_document(doc)

    assert repo.get_document(tenant_id, "doc-1") is not None
    assert repo.get_document(other_tenant, "doc-1") is None

    v1 = EmbeddingVector.from_list([1.0, 0.0])
    v2 = EmbeddingVector.from_list([0.0, 1.0])
    chunks = [
        DocumentChunk("chk-1", "doc-1", tenant_id, 0, "FastAPI and Clean Architecture", v1),
        DocumentChunk("chk-2", "doc-1", tenant_id, 1, "MSSQL relational vector indexing", v2),
    ]
    repo.save_chunks(chunks)

    stored = repo.get_chunks_by_document(tenant_id, "doc-1")
    assert len(stored) == 2

    # Scoped search
    matches = repo.search_hybrid(
        tenant_id=other_tenant,
        query_text="FastAPI",
        query_vector=v1,
    )
    assert len(matches) == 0

    matches = repo.search_hybrid(
        tenant_id=tenant_id,
        query_text="FastAPI architecture",
        query_vector=v1,
        top_k=2,
    )
    assert len(matches) > 0
    top_chunk, score = matches[0]
    assert top_chunk.id == "chk-1"
    assert score > 0.7


@pytest.mark.anyio
async def test_embedding_client_contract() -> None:
    client = FakeEmbeddingClient(dimension=4)
    texts = ["hello world", "rag vector search"]

    vectors = await client.generate_embeddings(texts)

    assert len(vectors) == 2
    assert all(isinstance(v, EmbeddingVector) for v in vectors)
    assert vectors[0].dimensions == 4
