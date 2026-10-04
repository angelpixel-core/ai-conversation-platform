"""Index document chunks command and handler for asynchronous chunking and embedding."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.exceptions import DocumentNotFoundError, DocumentValidationError
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class ChunkInput:
    """Input payload for a single chunk."""

    content: str
    page_number: int | None = None
    chunk_id: str | None = None


@dataclass(frozen=True)
class IndexDocumentChunksCommand:
    """Command to index a list of chunks for an existing document."""

    tenant_id: str
    document_id: str
    chunks: Sequence[ChunkInput]


@dataclass(frozen=True)
class IndexDocumentChunksResult:
    """Result of indexing chunks for a document."""

    document_id: str
    total_chunks: int
    status: str


class IndexDocumentChunksCommandHandler:
    """Handles generating embeddings and saving chunks for a document."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        embedding_client: EmbeddingClientPort,
    ) -> None:
        """Initializes the chunk indexing handler.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
            embedding_client: Driven port for vector embedding generation.
        """
        self._unit_of_work = unit_of_work
        self._embedding_client = embedding_client

    async def handle(self, command: IndexDocumentChunksCommand) -> IndexDocumentChunksResult:
        """Processes chunks, generates embeddings, and persists indexed knowledge.

        Args:
            command: IndexDocumentChunksCommand payload.

        Returns:
            IndexDocumentChunksResult with indexing status.

        Raises:
            DocumentValidationError: If chunks list is empty.
            DocumentNotFoundError: If referenced document does not exist.
        """
        if not command.chunks:
            raise DocumentValidationError("La lista de fragmentos a indexar no puede estar vacía.")

        tenant_id = TenantId(command.tenant_id)

        with self._unit_of_work as uow:
            doc = uow.knowledge.get_document(tenant_id, command.document_id)
            if doc is None:
                raise DocumentNotFoundError(f"Documento '{command.document_id}' no encontrado.")

            doc.mark_processing()
            uow.knowledge.save_document(doc)
            uow.commit()

        try:
            texts = [c.content for c in command.chunks]
            embeddings = await self._embedding_client.generate_embeddings(texts)

            doc_chunks = [
                DocumentChunk(
                    chunk_id=c.chunk_id or f"chk_{uuid4().hex[:12]}",
                    document_id=command.document_id,
                    tenant_id=tenant_id,
                    sequence_number=idx,
                    content=c.content,
                    embedding=embeddings[idx],
                    page_number=c.page_number,
                )
                for idx, c in enumerate(command.chunks)
            ]

            with self._unit_of_work as uow:
                doc = uow.knowledge.get_document(tenant_id, command.document_id)
                if doc is None:
                    raise DocumentNotFoundError(f"Documento '{command.document_id}' no encontrado.")

                uow.knowledge.save_chunks(doc_chunks)
                doc.mark_indexed(total_chunks=len(doc_chunks))
                uow.knowledge.save_document(doc)
                uow.commit()

                return IndexDocumentChunksResult(
                    document_id=doc.id,
                    total_chunks=doc.total_chunks,
                    status=doc.status.value,
                )
        except Exception:
            with self._unit_of_work as uow:
                doc = uow.knowledge.get_document(tenant_id, command.document_id)
                if doc is not None:
                    doc.mark_failed()
                    uow.knowledge.save_document(doc)
                    uow.commit()
            raise


__all__ = [
    "ChunkInput",
    "IndexDocumentChunksCommand",
    "IndexDocumentChunksCommandHandler",
    "IndexDocumentChunksResult",
]
