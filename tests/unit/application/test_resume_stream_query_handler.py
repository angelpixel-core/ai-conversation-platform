"""Unit tests for ResumeStreamQuery and ResumeStreamQueryHandler."""

import pytest
from src.application.conversations.queries.resume_stream_query import (
    ResumeStreamQuery,
)
from src.application.conversations.queries.resume_stream_query_handler import (
    ResumeStreamQueryHandler,
)

from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk


class FakeStreamBufferRepo(StreamBufferRepositoryPort):
    def __init__(self) -> None:
        self.chunks: list[StreamChunk] = []

    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        self.chunks.append(chunk)

    async def get_chunks_since(self, stream_id: str, since_sequence: int) -> list[StreamChunk]:
        return [c for c in self.chunks if c.sequence_number > since_sequence]

    async def is_stream_completed(self, stream_id: str) -> bool:
        return any(c.is_final for c in self.chunks)


def test_resume_stream_query_validation() -> None:
    query = ResumeStreamQuery(stream_id="stream-123", last_event_id=5)
    assert query.stream_id == "stream-123"
    assert query.last_event_id == 5

    # Invalid empty stream_id
    with pytest.raises(ValueError, match="stream_id cannot be empty"):
        ResumeStreamQuery(stream_id="")

    with pytest.raises(ValueError, match="stream_id cannot be empty"):
        ResumeStreamQuery(stream_id="   ")

    # Invalid negative last_event_id (< -1)
    with pytest.raises(ValueError, match="last_event_id must be >= -1"):
        ResumeStreamQuery(stream_id="valid", last_event_id=-2)


@pytest.mark.anyio
async def test_resume_stream_query_handler_streams_from_last_event_id() -> None:
    repo = FakeStreamBufferRepo()
    await repo.append_chunk("conv-abc", StreamChunk.create(0, "A"))
    await repo.append_chunk("conv-abc", StreamChunk.create(1, "B"))
    await repo.append_chunk("conv-abc", StreamChunk.create(2, "C", is_final=True))

    recovery_service = StreamRecoveryService(buffer_repo=repo, poll_interval_seconds=0.01)
    handler = ResumeStreamQueryHandler(recovery_service=recovery_service)

    query = ResumeStreamQuery(stream_id="conv-abc", last_event_id=0)
    chunks: list[StreamChunk] = []
    async for chunk in handler.handle(query):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert [c.content for c in chunks] == ["B", "C"]
    assert chunks[-1].is_final is True


@pytest.mark.anyio
async def test_resume_stream_query_handler_defaults_to_all_chunks_when_none() -> None:
    repo = FakeStreamBufferRepo()
    await repo.append_chunk("conv-all", StreamChunk.create(0, "Start"))
    await repo.append_chunk("conv-all", StreamChunk.create(1, "End", is_final=True))

    recovery_service = StreamRecoveryService(buffer_repo=repo, poll_interval_seconds=0.01)
    handler = ResumeStreamQueryHandler(recovery_service=recovery_service)

    query = ResumeStreamQuery(stream_id="conv-all", last_event_id=None)
    chunks: list[StreamChunk] = []
    async for chunk in handler.handle(query):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert [c.content for c in chunks] == ["Start", "End"]
