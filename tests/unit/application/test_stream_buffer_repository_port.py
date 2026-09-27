"""Unit contract tests for StreamBufferRepositoryPort."""

import pytest

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk


class FakeStreamBufferRepository(StreamBufferRepositoryPort):
    """Fake repository to test adherence to StreamBufferRepositoryPort contract."""

    def __init__(self) -> None:
        self.buffers: dict[str, list[StreamChunk]] = {}

    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        self.buffers.setdefault(stream_id, []).append(chunk)

    async def get_chunks_since(self, stream_id: str, since_sequence: int) -> list[StreamChunk]:
        chunks = self.buffers.get(stream_id, [])
        return [c for c in chunks if c.sequence_number > since_sequence]

    async def is_stream_completed(self, stream_id: str) -> bool:
        chunks = self.buffers.get(stream_id, [])
        return any(c.is_final for c in chunks)


@pytest.mark.anyio
async def test_stream_buffer_repository_port_contract() -> None:
    repo = FakeStreamBufferRepository()
    assert isinstance(repo, StreamBufferRepositoryPort)

    stream_id = "stream-conv-1"
    c0 = StreamChunk.create(sequence_number=0, content="First ")
    c1 = StreamChunk.create(sequence_number=1, content="Second ")
    c2 = StreamChunk.create(sequence_number=2, content="Final", is_final=True)

    await repo.append_chunk(stream_id, c0)
    await repo.append_chunk(stream_id, c1)
    await repo.append_chunk(stream_id, c2)

    # Client reconnects after chunk 0
    missed = await repo.get_chunks_since(stream_id, since_sequence=0)
    assert len(missed) == 2
    assert [c.sequence_number for c in missed] == [1, 2]

    completed = await repo.is_stream_completed(stream_id)
    assert completed is True
