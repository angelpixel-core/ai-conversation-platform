"""Value Object for StreamChunk in DDD.

Rules:
- Immutable by design (@dataclass(frozen=True)).
- Represents an individual sequenced chunk within an LLM streaming response.
- Guarantees sequence ordering and resilient resumption.
- Zero external framework dependencies (standard library only).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class StreamChunk:
    """Individual versioned chunk of a streaming response."""

    chunk_id: str
    sequence_number: int
    content: str
    is_final: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.chunk_id.strip():
            raise ValueError("El chunk_id no puede estar vacío.")
        if self.sequence_number < 0:
            raise ValueError("El número de secuencia no puede ser negativo.")
        if not self.is_final and not self.content:
            raise ValueError("Un fragmento intermedio no puede tener contenido vacío.")

        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=UTC))

    @classmethod
    def create(
        cls,
        sequence_number: int,
        content: str,
        is_final: bool = False,
        chunk_id: str | None = None,
    ) -> "StreamChunk":
        """Factory method to construct a new StreamChunk with UUIDv4 if not provided."""
        return cls(
            chunk_id=chunk_id or str(uuid.uuid4()),
            sequence_number=sequence_number,
            content=content,
            is_final=is_final,
            created_at=datetime.now(UTC),
        )
