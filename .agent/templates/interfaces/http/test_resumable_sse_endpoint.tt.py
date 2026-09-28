"""Test template canónico para Resumable SSE Streaming Endpoint."""

from fastapi import HTTPException
import pytest

from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from .resumable_sse_endpoint import format_sse_chunk, parse_last_event_id


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
