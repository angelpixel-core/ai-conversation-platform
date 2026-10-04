"""In-memory implementation of the StreamBufferRepositoryPort.

Rules:
- Belongs to src/infrastructure/persistence/in_memory/.
- Implements StreamBufferRepositoryPort.
- Provides volatile in-memory storage for unit tests and local development.
"""

from collections import defaultdict

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk


class InMemoryStreamBufferRepositoryAdapter(StreamBufferRepositoryPort):
    """In-memory adapter for the stream buffer repository port."""

    def __init__(self) -> None:
        self._buffers: dict[str, list[StreamChunk]] = defaultdict(list)

    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        if chunk.sequence_number == 1:
            self._buffers[stream_id].clear()
        self._buffers[stream_id].append(chunk)

    async def get_chunks_since(self, stream_id: str, since_sequence: int) -> list[StreamChunk]:
        chunks = self._buffers.get(stream_id, [])
        return [c for c in chunks if c.sequence_number > since_sequence]

    async def is_stream_completed(self, stream_id: str) -> bool:
        chunks = self._buffers.get(stream_id, [])
        return any(c.is_final for c in chunks)

    def all_chunks(self, stream_id: str) -> list[StreamChunk]:
        """Inspection helper for unit tests."""
        return list(self._buffers.get(stream_id, []))


# Backward compatible alias
InMemoryStreamBufferRepository = InMemoryStreamBufferRepositoryAdapter
