"""Unit tests for Citation Value Object."""

import pytest

from src.domain.knowledge.value_objects.citation import Citation


def test_citation_creation_valid() -> None:
    citation = Citation(
        source_document_id="doc-123",
        document_name="architecture_handbook.pdf",
        chunk_id="chunk-456",
        page_number=12,
        similarity_score=0.91,
        snippet="Clean Architecture isolates domain rules from frameworks.",
    )

    assert citation.source_document_id == "doc-123"
    assert citation.document_name == "architecture_handbook.pdf"
    assert citation.chunk_id == "chunk-456"
    assert citation.page_number == 12
    assert citation.similarity_score == 0.91
    assert citation.snippet == "Clean Architecture isolates domain rules from frameworks."


def test_citation_optional_page_number_allowed() -> None:
    citation = Citation(
        source_document_id="doc-123",
        document_name="architecture_handbook.pdf",
        chunk_id="chunk-456",
        page_number=None,
        similarity_score=0.85,
        snippet="Snippet without page number.",
    )
    assert citation.page_number is None


@pytest.mark.parametrize(
    ("doc_id", "doc_name", "chunk_id", "score", "snippet", "error_match"),
    [
        ("", "doc.pdf", "chk-1", 0.8, "text", "source_document_id"),
        ("doc-1", "", "chk-1", 0.8, "text", "nombre del documento"),
        ("doc-1", "doc.pdf", "", 0.8, "text", "chunk_id"),
        ("doc-1", "doc.pdf", "chk-1", -0.1, "text", "similarity_score"),
        ("doc-1", "doc.pdf", "chk-1", 1.1, "text", "similarity_score"),
        ("doc-1", "doc.pdf", "chk-1", 0.8, "   ", "snippet"),
    ],
)
def test_citation_invalid_inputs_raise_value_error(
    doc_id: str,
    doc_name: str,
    chunk_id: str,
    score: float,
    snippet: str,
    error_match: str,
) -> None:
    with pytest.raises(ValueError, match=error_match):
        Citation(
            source_document_id=doc_id,
            document_name=doc_name,
            chunk_id=chunk_id,
            page_number=1,
            similarity_score=score,
            snippet=snippet,
        )


def test_citation_immutable() -> None:
    citation = Citation(
        source_document_id="doc-1",
        document_name="doc.pdf",
        chunk_id="chk-1",
        page_number=1,
        similarity_score=0.8,
        snippet="Text",
    )
    with pytest.raises(AttributeError):
        citation.similarity_score = 0.9  # type: ignore[misc]
