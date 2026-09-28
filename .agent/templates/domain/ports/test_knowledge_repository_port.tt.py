"""Canonical test template: KnowledgeRepositoryPort contract verification."""

from typing import Sequence

import pytest
from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
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

            # Semantic score
            v_score = query_vector.cosine_similarity(chunk.embedding)

            # Lexical score (token overlap ratio)
            content_lower = chunk.content.lower()
            matches = sum(1 for t in tokens if t in content_lower)
            l_score = matches / len(tokens) if tokens else 0.0

            hybrid_score = (alpha * v_score) + ((1.0 - alpha) * l_score)
            if hybrid_score >= min_score:
                results.append((chunk, hybrid_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


def test_knowledge_repository_contract_document_and_chunks() -> None:
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

    # Cross-tenant chunk search returns empty
    matches = repo.search_hybrid(
        tenant_id=other_tenant,
        query_text="FastAPI",
        query_vector=v1,
    )
    assert len(matches) == 0

    # Matching tenant search returns top result
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
