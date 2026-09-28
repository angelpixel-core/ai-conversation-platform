"""Test template canónico para StreamRecoveryService."""

import anyio
import pytest

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from .stream_recovery_service import StreamRecoveryService


class FakeStreamBufferRepo(StreamBufferRepositoryPort):
    def __init__(self) -> None:
        self.chunks: list[StreamChunk] = []

    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        self.chunks.append(chunk)

    async def get_chunks_since(
        self, stream_id: str, since_sequence: int
    ) -> list[StreamChunk]:
        return [c for c in self.chunks if c.sequence_number > since_sequence]

    async def is_stream_completed(self, stream_id: str) -> bool:
        return any(c.is_final for c in self.chunks)


@pytest.mark.anyio
async def test_stream_recovery_service_recovers_buffered_chunks() -> None:
    repo = FakeStreamBufferRepo()
    await repo.append_chunk("s1", StreamChunk.create(0, "A"))
    await repo.append_chunk("s1", StreamChunk.create(1, "B"))
    await repo.append_chunk("s1", StreamChunk.create(2, "C", is_final=True))

    service = StreamRecoveryService(buffer_repo=repo, poll_interval_seconds=0.01)

    # El cliente se reconecta habiendo visto la secuencia 0 (espera chunks 1 y 2)
    emitted: list[StreamChunk] = []
    async for chunk in service.recover_stream(stream_id="s1", since_sequence=0):
        emitted.append(chunk)

    assert len(emitted) == 2
    assert [c.content for c in emitted] == ["B", "C"]
    assert emitted[-1].is_final is True


@pytest.mark.anyio
async def test_stream_recovery_service_handles_progressive_emission() -> None:
    repo = FakeStreamBufferRepo()
    service = StreamRecoveryService(buffer_repo=repo, poll_interval_seconds=0.01)

    emitted: list[StreamChunk] = []

    async def consumer() -> None:
        async for chunk in service.recover_stream(stream_id="s2", since_sequence=-1):
            emitted.append(chunk)

    async def producer() -> None:
        await anyio.sleep(0.02)
        await repo.append_chunk("s2", StreamChunk.create(0, "Chunk 1"))
        await anyio.sleep(0.02)
        await repo.append_chunk("s2", StreamChunk.create(1, "Chunk 2", is_final=True))

    async with anyio.create_task_group() as tg:
        tg.start_soon(consumer)
        tg.start_soon(producer)

    assert len(emitted) == 2
    assert [c.content for c in emitted] == ["Chunk 1", "Chunk 2"]
