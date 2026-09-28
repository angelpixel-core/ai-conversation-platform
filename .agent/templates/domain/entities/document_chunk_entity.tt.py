"""Canonical template: DocumentChunk Entity."""

from datetime import UTC, datetime

from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId


class DocumentChunk:
    """Represents a text chunk of a document with its vector embedding."""

    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        tenant_id: TenantId,
        sequence_number: int,
        content: str,
        embedding: EmbeddingVector,
        page_number: int | None = None,
        created_at: datetime | None = None,
    ) -> None:
        if not chunk_id.strip():
            raise ValueError("El chunk_id no puede estar vacío.")
        if not document_id.strip():
            raise ValueError("El document_id no puede estar vacío.")
        if sequence_number < 0:
            raise ValueError("El sequence_number debe ser mayor o igual a cero.")
        if not content.strip():
            raise ValueError("El contenido del fragmento no puede estar vacío.")

        self._id = chunk_id.strip()
        self._document_id = document_id.strip()
        self._tenant_id = tenant_id
        self._sequence_number = sequence_number
        self._content = content.strip()
        self._embedding = embedding
        self._page_number = page_number
        self._created_at = created_at or datetime.now(UTC)

    @property
    def id(self) -> str:
        return self._id

    @property
    def document_id(self) -> str:
        return self._document_id

    @property
    def tenant_id(self) -> TenantId:
        return self._tenant_id

    @property
    def sequence_number(self) -> int:
        return self._sequence_number

    @property
    def content(self) -> str:
        return self._content

    @property
    def embedding(self) -> EmbeddingVector:
        return self._embedding

    @property
    def page_number(self) -> int | None:
        return self._page_number

    @property
    def created_at(self) -> datetime:
        return self._created_at
