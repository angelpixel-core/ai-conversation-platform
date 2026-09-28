"""Unit tests for Resumable SSE Streaming Endpoint."""

import pytest
from fastapi import HTTPException

from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.infrastructure.persistence.in_memory.in_memory_stream_buffer_repository import (
    InMemoryStreamBufferRepositoryAdapter,
)
from src.interfaces.http.resumable_sse_endpoint import (
    build_resumable_sse_response,
    format_sse_chunk,
    parse_last_event_id,
)


def test_format_sse_chunk() -> None:
    chunk = StreamChunk.create(
        sequence_number=5,
        content="Respuesta en curso",
        is_final=False,
    )
    formatted = format_sse_chunk(chunk)
    assert formatted.startswith("id: 5\n")
    assert "event: message\n" in formatted
    assert '"content": "Respuesta en curso"' in formatted
    assert formatted.endswith("\n\n")


def test_parse_last_event_id_valid() -> None:
    assert parse_last_event_id(None) == -1
    assert parse_last_event_id("0") == 0
    assert parse_last_event_id("42") == 42


def test_parse_last_event_id_invalid() -> None:
    with pytest.raises(HTTPException) as exc_info:
        parse_last_event_id("invalid-number")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info_neg:
        parse_last_event_id("-5")
    assert exc_info_neg.value.status_code == 400


@pytest.mark.anyio
async def test_build_resumable_sse_response() -> None:
    buffer_repo = InMemoryStreamBufferRepositoryAdapter()
    await buffer_repo.append_chunk("stream-1", StreamChunk.create(0, "A"))
    await buffer_repo.append_chunk("stream-1", StreamChunk.create(1, "B"))
    await buffer_repo.append_chunk("stream-1", StreamChunk.create(2, "C", is_final=True))

    service = StreamRecoveryService(buffer_repo=buffer_repo, poll_interval_seconds=0.01)

    response = await build_resumable_sse_response(
        stream_id="stream-1",
        recovery_service=service,
        last_event_id="0",
    )

    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"

    body_chunks = [chunk async for chunk in response.body_iterator]
    full_body = "".join(
        chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk) for chunk in body_chunks
    )
    assert "id: 1\n" in full_body
    assert "id: 2\n" in full_body
    assert "id: 0\n" not in full_body
