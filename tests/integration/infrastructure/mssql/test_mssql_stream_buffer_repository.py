"""Integration tests for MssqlStreamBufferRepositoryAdapter against live SQL Server."""

import pytest
from sqlalchemy.engine import Engine

from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.infrastructure.persistence.mssql.connection import (
    create_session_factory,
)
from src.infrastructure.persistence.mssql.stream_buffer_repository import (
    MssqlStreamBufferRepositoryAdapter,
)


@pytest.mark.anyio
async def test_mssql_stream_buffer_repository_real_db(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)
    stream_id = "real-mssql-stream-1"

    chunk0 = StreamChunk.create(0, "Live chunk 0")
    chunk1 = StreamChunk.create(1, "Live chunk 1")
    chunk2 = StreamChunk.create(2, "Live chunk 2", is_final=True)

    with session_factory() as session:
        repo = MssqlStreamBufferRepositoryAdapter(session=session)
        await repo.append_chunk(stream_id, chunk0)
        await repo.append_chunk(stream_id, chunk1)
        await repo.append_chunk(stream_id, chunk2)

    with session_factory() as session:
        repo = MssqlStreamBufferRepositoryAdapter(session=session)
        assert await repo.is_stream_completed(stream_id) is True

        chunks = await repo.get_chunks_since(stream_id, since_sequence=0)
        assert len(chunks) == 2
        assert [c.content for c in chunks] == ["Live chunk 1", "Live chunk 2"]
        assert chunks[-1].is_final is True
