"""Unit tests for MSSQL DocumentModel and DocumentChunkModel."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.infrastructure.persistence.mssql.models import (
    DocumentChunkModel,
    DocumentModel,
)


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_document_model_instantiation_and_persistence(sqlite_session: Session) -> None:
    doc = DocumentModel(
        id="doc-123",
        tenant_id="corp-acme",
        filename="handbook.pdf",
        content_type="application/pdf",
        status="PENDING",
        total_chunks=0,
    )
    sqlite_session.add(doc)
    sqlite_session.commit()

    retrieved = sqlite_session.exec(
        select(DocumentModel).where(DocumentModel.id == "doc-123")
    ).first()
    assert retrieved is not None
    assert retrieved.id == "doc-123"
    assert retrieved.tenant_id == "corp-acme"
    assert retrieved.filename == "handbook.pdf"
    assert retrieved.content_type == "application/pdf"
    assert retrieved.status == "PENDING"
    assert retrieved.total_chunks == 0
    assert isinstance(retrieved.created_at, datetime)
    assert isinstance(retrieved.updated_at, datetime)


def test_document_chunk_model_persistence(sqlite_session: Session) -> None:
    doc = DocumentModel(
        id="doc-100",
        tenant_id="corp-acme",
        filename="spec.txt",
        content_type="text/plain",
        status="INDEXED",
        total_chunks=1,
    )
    chunk = DocumentChunkModel(
        id="chk-1",
        tenant_id="corp-acme",
        document_id="doc-100",
        sequence_number=0,
        content="Antigravity clean architecture.",
        embedding_json="[0.6, 0.8]",
        page_number=1,
    )
    sqlite_session.add(doc)
    sqlite_session.add(chunk)
    sqlite_session.commit()

    retrieved = sqlite_session.exec(
        select(DocumentChunkModel).where(DocumentChunkModel.id == "chk-1")
    ).first()
    assert retrieved is not None
    assert retrieved.id == "chk-1"
    assert retrieved.tenant_id == "corp-acme"
    assert retrieved.document_id == "doc-100"
    assert retrieved.sequence_number == 0
    assert retrieved.content == "Antigravity clean architecture."
    assert retrieved.embedding_json == "[0.6, 0.8]"
    assert retrieved.page_number == 1
