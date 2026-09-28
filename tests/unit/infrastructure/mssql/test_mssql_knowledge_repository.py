"""Unit tests for MssqlKnowledgeRepository adapter."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.mssql_knowledge_repository import (
    MssqlKnowledgeRepository,
)


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_mssql_knowledge_repo_save_and_get_document(sqlite_session: Session) -> None:
    repo = MssqlKnowledgeRepository(session=sqlite_session)
    tid = TenantId("tenant-acme")
    other_tid = TenantId("tenant-other")

    doc = Document.create("doc-1", tid, "policy.pdf")
    repo.save_document(doc)
    sqlite_session.commit()

    retrieved = repo.get_document(tid, "doc-1")
    assert retrieved is not None
    assert retrieved.id == "doc-1"
    assert retrieved.filename == "policy.pdf"

    # Scoped by tenant
    assert repo.get_document(other_tid, "doc-1") is None


def test_mssql_knowledge_repo_chunks_and_hybrid_search(sqlite_session: Session) -> None:
    repo = MssqlKnowledgeRepository(session=sqlite_session)
    tid = TenantId("tenant-acme")
    other_tid = TenantId("tenant-other")

    doc = Document.create("doc-10", tid, "manual.pdf")
    repo.save_document(doc)

    v1 = EmbeddingVector.from_list([1.0, 0.0])
    v2 = EmbeddingVector.from_list([0.0, 1.0])

    chunks = [
        DocumentChunk(
            "chk-1", "doc-10", tid, 0, "Python Clean Architecture DDD", v1, page_number=1
        ),
        DocumentChunk(
            "chk-2", "doc-10", tid, 1, "MSSQL relational vector tables", v2, page_number=2
        ),
    ]
    repo.save_chunks(chunks)
    sqlite_session.commit()

    retrieved_chunks = repo.get_chunks_by_document(tid, "doc-10")
    assert len(retrieved_chunks) == 2

    # Cross-tenant search returns empty
    matches = repo.search_hybrid(
        tenant_id=other_tid,
        query_text="Architecture",
        query_vector=v1,
    )
    assert len(matches) == 0

    # Scoped tenant hybrid search
    matches = repo.search_hybrid(
        tenant_id=tid,
        query_text="Architecture Python",
        query_vector=v1,
        top_k=2,
        min_score=0.5,
    )
    assert len(matches) > 0
    top_chunk, score = matches[0]
    assert top_chunk.id == "chk-1"
    assert score > 0.7
