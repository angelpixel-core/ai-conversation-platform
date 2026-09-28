"""Integration tests for SSE stream reconnection using Last-Event-ID."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.infrastructure.persistence.in_memory.in_memory_stream_buffer_repository import (
    InMemoryStreamBufferRepositoryAdapter,
)
from src.interfaces.http.api import build_api


@pytest.mark.anyio
async def test_stream_reconnection_with_last_event_id() -> None:
    buffer_repo = InMemoryStreamBufferRepositoryAdapter()
    conv_id = str(uuid4())

    await buffer_repo.append_chunk(conv_id, StreamChunk.create(0, "First chunk"))
    await buffer_repo.append_chunk(conv_id, StreamChunk.create(1, "Second chunk"))
    await buffer_repo.append_chunk(conv_id, StreamChunk.create(2, "Third chunk", is_final=True))

    recovery_service = StreamRecoveryService(buffer_repo=buffer_repo, poll_interval_seconds=0.01)

    app = build_api(
        stream_recovery_service=recovery_service,
    )
    client = TestClient(app)

    # Client reconnects having previously received event id 0
    resp = client.get(
        f"/conversations/{conv_id}/stream",
        headers={"Last-Event-ID": "0"},
    )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    body = resp.text
    # Should only receive event 1 and 2
    assert "id: 1\n" in body
    assert "id: 2\n" in body
    assert "Second chunk" in body
    assert "Third chunk" in body
    assert "First chunk" not in body


@pytest.mark.anyio
async def test_stream_reconnection_invalid_last_event_id_returns_400() -> None:
    buffer_repo = InMemoryStreamBufferRepositoryAdapter()
    conv_id = str(uuid4())
    recovery_service = StreamRecoveryService(buffer_repo=buffer_repo, poll_interval_seconds=0.01)

    app = build_api(
        stream_recovery_service=recovery_service,
    )
    client = TestClient(app)

    resp = client.get(
        f"/conversations/{conv_id}/stream",
        headers={"Last-Event-ID": "not-a-number"},
    )
    assert resp.status_code == 400
