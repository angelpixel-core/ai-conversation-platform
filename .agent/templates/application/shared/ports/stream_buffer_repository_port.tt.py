"""Template canónico para StreamBufferRepositoryPort (Application Port).

Reglas:
- Pertenece a src/application/shared/ports/.
- Abstracción para persistir y consultar fragmentos ordenados de un stream LLM.
- Permite a clientes reconectados recuperar chunks perdidos a partir de un sequence_number.
"""

from abc import ABC, abstractmethod

from src.domain.conversations.value_objects.stream_chunk import StreamChunk


class StreamBufferRepositoryPort(ABC):
    """Puerto de persistencia para el buffer de chunks de streaming."""

    @abstractmethod
    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        """Añade un fragmento ordenado al buffer del stream."""
        raise NotImplementedError

    @abstractmethod
    async def get_chunks_since(
        self, stream_id: str, since_sequence: int
    ) -> list[StreamChunk]:
        """Recupera todos los chunks ordenados cuyo sequence_number sea estrictamente mayor a since_sequence."""
        raise NotImplementedError

    @abstractmethod
    async def is_stream_completed(self, stream_id: str) -> bool:
        """Determina si el stream ha emitido ya su chunk final."""
        raise NotImplementedError
