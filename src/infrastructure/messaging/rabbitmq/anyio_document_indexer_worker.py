"""Asynchronous document indexer worker leveraging AnyIO for concurrent batch processing."""

import logging
from typing import Any

import anyio

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.exceptions import DocumentNotFoundError
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.shared.events.event_envelope import EventEnvelope
from src.domain.tenants.value_objects.tenant_id import TenantId

logger = logging.getLogger(__name__)


class AnyioDocumentIndexerWorker:
    """Consumes document upload events, chunks text, generates embeddings, and persists chunks."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        embedding_client: EmbeddingClientPort,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        concurrency_limit: int = 5,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._embedding_client = embedding_client
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._concurrency_limit = concurrency_limit

    def split_text_into_chunks(
        self,
        text: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[str]:
        """Splits source text into overlapping chunks of characters."""
        size = chunk_size or self._chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self._chunk_overlap

        if not text:
            return []
        if len(text) <= size:
            return [text]

        step = max(1, size - overlap)
        chunks: list[str] = []
        for i in range(0, len(text), step):
            chunk = text[i : i + size]
            if chunk:
                chunks.append(chunk)
            if i + size >= len(text):
                break
        return chunks

    def _mark_processing(self, tenant_id: TenantId, document_id: str) -> Document:
        """Fetches document and marks it as PROCESSING."""
        with self._unit_of_work:
            doc = self._unit_of_work.knowledge.get_document(tenant_id, document_id)
            if doc is None:
                raise DocumentNotFoundError(
                    f"Document '{document_id}' not found for tenant '{tenant_id}'."
                )
            doc.mark_processing()
            self._unit_of_work.knowledge.save_document(doc)
            self._unit_of_work.commit()
            return doc

    def _mark_failed(self, doc: Document) -> None:
        """Marks document as FAILED and commits."""
        with self._unit_of_work:
            doc.mark_failed()
            self._unit_of_work.knowledge.save_document(doc)
            self._unit_of_work.commit()

    def _save_indexed_chunks(self, doc: Document, chunks: list[DocumentChunk]) -> None:
        """Persists generated chunks and marks document as INDEXED."""
        with self._unit_of_work:
            self._unit_of_work.knowledge.save_chunks(chunks)
            doc.mark_indexed(total_chunks=len(chunks))
            self._unit_of_work.knowledge.save_document(doc)
            self._unit_of_work.commit()

    async def _embed_chunks_concurrently(self, chunk_texts: list[str]) -> list[EmbeddingVector]:
        """Generates embeddings for chunk texts concurrently using AnyIO task group."""
        embeddings: list[EmbeddingVector | None] = [None] * len(chunk_texts)
        semaphore = anyio.Semaphore(self._concurrency_limit)
        batch_size = 5

        async def _embed_batch(start_idx: int, batch: list[str]) -> None:
            async with semaphore:
                batch_embeddings = await self._embedding_client.generate_embeddings(batch)
                for offset, emb in enumerate(batch_embeddings):
                    embeddings[start_idx + offset] = emb

        async with anyio.create_task_group() as tg:
            for start_idx in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[start_idx : start_idx + batch_size]
                tg.start_soon(_embed_batch, start_idx, batch)

        return [emb for emb in embeddings if emb is not None]

    async def process_document_event(self, envelope: EventEnvelope | dict[str, Any]) -> int:
        """Processes document uploaded event, orchestrating chunking, embedding, and indexing."""
        payload: dict[str, Any] = (
            envelope.payload
            if isinstance(envelope, EventEnvelope)
            else envelope.get("payload", envelope)
        )

        tenant_id_str = str(payload.get("tenant_id", "")).strip()
        document_id = str(payload.get("document_id", "")).strip()
        content = str(payload.get("content", ""))
        chunk_size = int(payload.get("chunk_size", self._chunk_size))
        chunk_overlap = int(payload.get("chunk_overlap", self._chunk_overlap))
        tenant_id = TenantId(tenant_id_str)

        doc = self._mark_processing(tenant_id, document_id)

        try:
            chunk_texts = self.split_text_into_chunks(
                content, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            if not chunk_texts and content:
                chunk_texts = [content]

            vectors = await self._embed_chunks_concurrently(chunk_texts)
            document_chunks = [
                DocumentChunk(
                    chunk_id=f"{document_id}-chunk-{idx}",
                    document_id=document_id,
                    tenant_id=tenant_id,
                    sequence_number=idx,
                    content=text_segment,
                    embedding=emb,
                    page_number=idx + 1,
                )
                for idx, (text_segment, emb) in enumerate(zip(chunk_texts, vectors, strict=True))
            ]

            self._save_indexed_chunks(doc, document_chunks)
            return len(document_chunks)

        except BaseExceptionGroup as eg:
            logger.error("Failed to index document %s: %s", document_id, eg)
            self._mark_failed(doc)
            if len(eg.exceptions) == 1:
                raise eg.exceptions[0] from None
            raise
        except Exception as exc:
            logger.error("Failed to index document %s: %s", document_id, exc)
            self._mark_failed(doc)
            raise
