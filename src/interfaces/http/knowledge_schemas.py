"""Pydantic v2 DTO schemas for Knowledge management and RAG streaming citations."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Payload for uploading a new knowledge document for indexing."""

    filename: str = Field(
        ..., min_length=1, max_length=255, description="Name of the uploaded document file."
    )
    content: str = Field(
        ..., min_length=1, description="Raw text content to be chunked and indexed."
    )
    content_type: str = Field(
        default="text/plain", max_length=100, description="MIME content type."
    )
    chunk_size: int = Field(default=500, gt=0, description="Target character size for text chunks.")
    chunk_overlap: int = Field(
        default=50, ge=0, description="Overlapping characters between adjacent chunks."
    )


class DocumentUploadResponse(BaseModel):
    """Response returned upon accepting a document for ingestion."""

    document_id: str
    tenant_id: str
    filename: str
    status: str
    message: str


class DocumentStatusResponse(BaseModel):
    """Response reporting document ingestion status and chunk count."""

    document_id: str
    tenant_id: str
    filename: str
    content_type: str
    status: str
    total_chunks: int
    created_at: datetime
    updated_at: datetime


class CitationSchema(BaseModel):
    """Schema representing a grounded document citation."""

    source_document_id: str
    document_name: str
    chunk_id: str
    page_number: int | None = None
    similarity_score: float
    snippet: str


__all__ = [
    "CitationSchema",
    "DocumentStatusResponse",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
]
