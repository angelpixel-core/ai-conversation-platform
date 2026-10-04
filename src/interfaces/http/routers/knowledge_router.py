"""FastAPI router for Knowledge document management and ingestion."""

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.knowledge.entities.document import Document
from src.domain.shared.events.event_envelope import EventEnvelope
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.messaging.rabbitmq.anyio_document_indexer_worker import (
    AnyioDocumentIndexerWorker,
)
from src.interfaces.http.knowledge_schemas import (
    DocumentStatusResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
)


def create_knowledge_router(
    unit_of_work: UnitOfWorkPort,
    indexer_worker: AnyioDocumentIndexerWorker | None = None,
) -> APIRouter:
    """Creates FastAPI APIRouter for tenant-scoped knowledge documents."""
    router = APIRouter(tags=["Knowledge"])

    @router.post(
        "/tenants/{tenant_id}/documents",
        response_model=DocumentUploadResponse,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Upload document for ingestion",
        description="Uploads a document to be embedded and indexed for RAG retrieval.",
    )
    async def upload_document(
        tenant_id: str,
        request: DocumentUploadRequest,
        background_tasks: BackgroundTasks,
    ) -> DocumentUploadResponse:
        doc_id = str(uuid4())
        tid = TenantId(tenant_id)

        doc = Document.create(
            document_id=doc_id,
            tenant_id=tid,
            filename=request.filename,
            content_type=request.content_type,
        )

        with unit_of_work:
            unit_of_work.knowledge.save_document(doc)
            unit_of_work.commit()

        if indexer_worker is not None:
            envelope = EventEnvelope(
                event_type="knowledge.document.uploaded",
                payload={
                    "tenant_id": tenant_id,
                    "document_id": doc_id,
                    "filename": request.filename,
                    "content": request.content,
                    "chunk_size": request.chunk_size,
                    "chunk_overlap": request.chunk_overlap,
                },
            )
            background_tasks.add_task(indexer_worker.process_document_event, envelope)

        return DocumentUploadResponse(
            document_id=doc_id,
            tenant_id=tenant_id,
            filename=request.filename,
            status=doc.status.value,
            message="Document accepted for indexing.",
        )

    @router.get(
        "/tenants/{tenant_id}/documents/{document_id}/status",
        response_model=DocumentStatusResponse,
        status_code=status.HTTP_200_OK,
        summary="Get document indexing status",
        description="Retrieves current lifecycle status and indexed chunk count for a document.",
    )
    def get_document_status(
        tenant_id: str,
        document_id: str,
    ) -> DocumentStatusResponse:
        tid = TenantId(tenant_id)
        with unit_of_work:
            doc = unit_of_work.knowledge.get_document(tid, document_id)
            if doc is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document '{document_id}' not found for tenant '{tenant_id}'.",
                )
            return DocumentStatusResponse(
                document_id=doc.id,
                tenant_id=str(doc.tenant_id),
                filename=doc.filename,
                content_type=doc.content_type,
                status=doc.status.value,
                total_chunks=doc.total_chunks,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )

    return router
