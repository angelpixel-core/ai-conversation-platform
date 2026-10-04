"""Unit tests for MssqlStreamBufferRepositoryAdapter adapter."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.infrastructure.persistence.mssql.stream_buffer_repository import (
    MssqlStreamBufferRepositoryAdapter,
)


@pytest.fixture(name="session")
def fixture_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.mark.anyio
async def test_mssql_stream_buffer_repository_append_and_query(session: Session) -> None:
    repo = MssqlStreamBufferRepositoryAdapter(session=session)
    assert isinstance(repo, StreamBufferRepositoryPort)

    stream_id = "stream-mssql-1"
    chunk0 = StreamChunk.create(0, "Hello")
    chunk1 = StreamChunk.create(1, " World")
    chunk2 = StreamChunk.create(2, "!", is_final=True)

    await repo.append_chunk(stream_id, chunk0)
    await repo.append_chunk(stream_id, chunk1)
    await repo.append_chunk(stream_id, chunk2)

    assert await repo.is_stream_completed(stream_id) is True

    # Retrieve all chunks since sequence 0
    subsequent = await repo.get_chunks_since(stream_id, since_sequence=0)
    assert len(subsequent) == 2
    assert [c.content for c in subsequent] == [" World", "!"]
    assert subsequent[-1].is_final is True
