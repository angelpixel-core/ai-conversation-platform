"""Upload document command and handler for registering knowledge files."""

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.knowledge.entities.document import Document
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class UploadDocumentCommand:
    """Command to upload and register a new document for a tenant."""

    tenant_id: str
    filename: str
    content_type: str = "text/plain"
    document_id: str | None = None


@dataclass(frozen=True)
class UploadDocumentResult:
    """Result of successfully registering a document."""

    document_id: str
    tenant_id: str
    filename: str
    status: str
    created_at: datetime


class UploadDocumentHandler:
    """Handles registering knowledge documents for background ingestion."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def handle(self, command: UploadDocumentCommand) -> UploadDocumentResult:
        tenant_id = TenantId(command.tenant_id)

        with self._unit_of_work as uow:
            tenant = uow.tenants.get(tenant_id)
            if tenant is None:
                raise ValueError(f"Inquilino '{command.tenant_id}' no encontrado.")

            document_id = command.document_id or f"doc_{uuid4().hex[:12]}"
            doc = Document.create(
                document_id=document_id,
                tenant_id=tenant_id,
                filename=command.filename,
                content_type=command.content_type,
            )

            uow.knowledge.save_document(doc)
            uow.commit()

            return UploadDocumentResult(
                document_id=doc.id,
                tenant_id=str(doc.tenant_id),
                filename=doc.filename,
                status=doc.status.value,
                created_at=doc.created_at,
            )
