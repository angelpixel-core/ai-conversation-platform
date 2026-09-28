"""Domain events for knowledge management, document indexing, and RAG grounding."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DocumentUploadedDomainEvent:
    """Emitted when a knowledge document is registered for processing."""

    document_id: str
    tenant_id: str
    filename: str
    content_type: str
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentIndexedDomainEvent:
    """Emitted when a document has been chunked, embedded, and indexed."""

    document_id: str
    tenant_id: str
    total_chunks: int
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentIndexingFailedDomainEvent:
    """Emitted when document chunking or embedding ingestion fails."""

    document_id: str
    tenant_id: str
    error_reason: str
    occurred_at: datetime


@dataclass(frozen=True)
class KnowledgeContextRetrievedDomainEvent:
    """Emitted when relevant knowledge chunks are retrieved and grounded into conversation."""

    tenant_id: str
    conversation_id: str
    query: str
    retrieved_chunk_ids: list[str]
    occurred_at: datetime
