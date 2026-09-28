"""Template canónico para Value Object StreamChunk (DDD).

Reglas:
- Inmutable por diseño (@dataclass(frozen=True)).
- Representa un fragmento incremental numerado dentro de un stream LLM.
- Permite ordenamiento determinista y reanudación desde secuencia específica.
- Sin dependencias de frameworks externos.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class StreamChunk:
    """Fragmento individual versionado de una respuesta en streaming."""

    chunk_id: str
    sequence_number: int
    content: str
    is_final: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.chunk_id.strip():
            raise ValueError("El chunk_id no puede estar vacío.")
        if self.sequence_number < 0:
            raise ValueError("El número de secuencia no puede ser negativo.")
        if not self.is_final and not self.content:
            raise ValueError("Un fragmento intermedio no puede tener contenido vacío.")

        if self.created_at.tzinfo is None:
            object.__setattr__(
                self, "created_at", self.created_at.replace(tzinfo=timezone.utc)
            )

    @classmethod
    def create(
        cls,
        sequence_number: int,
        content: str,
        is_final: bool = False,
        chunk_id: str | None = None,
    ) -> "StreamChunk":
        return cls(
            chunk_id=chunk_id or str(uuid.uuid4()),
            sequence_number=sequence_number,
            content=content,
            is_final=is_final,
            created_at=datetime.now(timezone.utc),
        )
