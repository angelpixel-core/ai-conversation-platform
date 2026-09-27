"""Port for Stream Buffer Repository in Application Layer.

Rules:
- Belongs to src/application/shared/ports/.
- Defines persistence contract for buffering and replaying sequenced LLM stream chunks.
- Enables seamless SSE client resumption from specific sequence numbers.
"""

from abc import ABC, abstractmethod

from src.domain.conversations.value_objects.stream_chunk import StreamChunk


class StreamBufferRepositoryPort(ABC):
    """Abstract port for managing LLM streaming chunk buffers."""

    @abstractmethod
    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        """Append a sequenced chunk to the stream buffer."""
        raise NotImplementedError

    @abstractmethod
    async def get_chunks_since(self, stream_id: str, since_sequence: int) -> list[StreamChunk]:
        """Fetch ordered chunks with sequence_number strictly greater than since_sequence."""
        raise NotImplementedError

    @abstractmethod
    async def is_stream_completed(self, stream_id: str) -> bool:
        """Determine whether the stream has reached its final chunk."""
        raise NotImplementedError
