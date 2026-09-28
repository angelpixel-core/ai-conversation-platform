"""Immutable representation of a grounded source citation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    """Immutable representation of a grounded source citation."""

    source_document_id: str
    document_name: str
    chunk_id: str
    page_number: int | None
    similarity_score: float
    snippet: str

    def __post_init__(self) -> None:
        if not self.source_document_id.strip():
            raise ValueError("El source_document_id no puede estar vacío.")
        if not self.document_name.strip():
            raise ValueError("El nombre del documento no puede estar vacío.")
        if not self.chunk_id.strip():
            raise ValueError("El chunk_id no puede estar vacío.")
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError("El similarity_score debe estar comprendido entre 0.0 y 1.0.")
        if not self.snippet.strip():
            raise ValueError("El snippet de la cita no puede estar vacío.")
