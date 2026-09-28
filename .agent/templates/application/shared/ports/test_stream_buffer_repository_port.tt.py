"""Test template canónico para StreamBufferRepositoryPort."""

import pytest

from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from .stream_buffer_repository_port import StreamBufferRepositoryPort


class FakeStreamBufferRepository(StreamBufferRepositoryPort):
    def __init__(self) -> None:
        self.buffers: dict[str, list[StreamChunk]] = {}

    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        self.buffers.setdefault(stream_id, []).append(chunk)

    async def get_chunks_since(
        self, stream_id: str, since_sequence: int
    ) -> list[StreamChunk]:
        chunks = self.buffers.get(stream_id, [])
        return [c for c in chunks if c.sequence_number > since_sequence]

    async def is_stream_completed(self, stream_id: str) -> bool:
        chunks = self.buffers.get(stream_id, [])
        return any(c.is_final for c in chunks)


@pytest.mark.anyio
async def test_stream_buffer_repository_contract() -> None:
    repo = FakeStreamBufferRepository()
    assert isinstance(repo, StreamBufferRepositoryPort)

    stream_id = "stream-1"
    c0 = StreamChunk.create(sequence_number=0, content="Inicio ")
    c1 = StreamChunk.create(sequence_number=1, content="del ")
    c2 = StreamChunk.create(sequence_number=2, content="stream.", is_final=True)

    await repo.append_chunk(stream_id, c0)
    await repo.append_chunk(stream_id, c1)
    await repo.append_chunk(stream_id, c2)

    # Cliente reconecta solicitando desde el chunk 0 (debe recibir 1 y 2)
    missed = await repo.get_chunks_since(stream_id, since_sequence=0)
    assert len(missed) == 2
    assert missed[0].sequence_number == 1
    assert missed[1].sequence_number == 2

    # Verificar si el stream concluyó
    completed = await repo.is_stream_completed(stream_id)
    assert completed is True
