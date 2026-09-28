"""Canonical test template: Citation Value Object."""

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
    assert citation.similarity_score == 0.91
    assert citation.page_number == 12


def test_citation_invalid_score_raises_value_error() -> None:
    with pytest.raises(ValueError, match="similarity_score"):
        Citation(
            source_document_id="doc-123",
            document_name="architecture_handbook.pdf",
            chunk_id="chunk-456",
            page_number=1,
            similarity_score=1.5,
            snippet="Valid snippet",
        )
