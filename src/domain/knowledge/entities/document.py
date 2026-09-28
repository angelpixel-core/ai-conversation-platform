"""Document aggregate root managing document ingestion and lifecycle."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from src.domain.knowledge.events.knowledge_events import (
    DocumentIndexedDomainEvent,
    DocumentUploadedDomainEvent,
)
from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.value_objects.tenant_id import TenantId


class DocumentStatus(StrEnum):
    """Lifecycle status of a knowledge document."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class Document(AggregateRoot):
    """Aggregate root managing ingestion and indexing of private knowledge documents."""

    def __init__(
        self,
        document_id: str,
        tenant_id: TenantId,
        filename: str,
        content_type: str = "text/plain",
        status: DocumentStatus = DocumentStatus.PENDING,
        total_chunks: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        if not filename.strip():
            raise ValueError("El nombre de archivo del documento no puede estar vacío.")

        self._id = document_id.strip()
        self._tenant_id = tenant_id
        self._filename = filename.strip()
        self._content_type = content_type
        self._status = status
        self._total_chunks = total_chunks
        self._created_at = created_at or datetime.now(UTC)
        self._updated_at = updated_at or self._created_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def content_type(self) -> str:
        return self._content_type

    @property
    def status(self) -> DocumentStatus:
        return self._status

    @property
    def total_chunks(self) -> int:
        return self._total_chunks

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def domain_events(self) -> list[Any]:
        return list(self._domain_events)

    @classmethod
    def create(
        cls,
        document_id: str,
        tenant_id: TenantId,
        filename: str,
        content_type: str = "text/plain",
    ) -> "Document":
        """Factory creating a new document in PENDING status and emitting upload event."""
        doc = cls(
            document_id=document_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            status=DocumentStatus.PENDING,
            total_chunks=0,
        )
        doc.record_event(
            DocumentUploadedDomainEvent(
                document_id=document_id,
                tenant_id=str(tenant_id),
                filename=doc.filename,
                content_type=doc.content_type,
                occurred_at=doc.created_at,
            )
        )
        return doc

    def mark_processing(self) -> None:
        """Transitions document status to PROCESSING."""
        self._status = DocumentStatus.PROCESSING
        self._updated_at = datetime.now(UTC)

    def mark_indexed(self, total_chunks: int) -> None:
        """Transitions document status to INDEXED with total chunk count."""
        if total_chunks <= 0:
            raise ValueError("El total de fragmentos indexados debe ser mayor a cero.")
        self._status = DocumentStatus.INDEXED
        self._total_chunks = total_chunks
        self._updated_at = datetime.now(UTC)
        self.record_event(
            DocumentIndexedDomainEvent(
                document_id=str(self._id),
                tenant_id=str(self._tenant_id),
                total_chunks=total_chunks,
                occurred_at=self._updated_at,
            )
        )

    def mark_failed(self) -> None:
        """Transitions document status to FAILED."""
        self._status = DocumentStatus.FAILED
        self._updated_at = datetime.now(UTC)
