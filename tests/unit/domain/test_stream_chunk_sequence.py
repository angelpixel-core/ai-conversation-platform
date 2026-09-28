"""Unit tests for StreamChunk Value Object and sequence ordering."""

from datetime import UTC, datetime

import pytest

from src.domain.conversations.value_objects.stream_chunk import StreamChunk


def test_stream_chunk_valid_creation() -> None:
    chunk = StreamChunk.create(
        sequence_number=1,
        content="Hola mundo",
        is_final=False,
    )
    assert chunk.sequence_number == 1
    assert chunk.content == "Hola mundo"
    assert chunk.is_final is False
    assert chunk.created_at.tzinfo is not None
    assert len(chunk.chunk_id) > 0


def test_stream_chunk_custom_id_and_timestamp() -> None:
    now = datetime(2026, 9, 27, 20, 0, 0, tzinfo=UTC)
    chunk = StreamChunk(
        chunk_id="custom-chunk-1",
        sequence_number=0,
        content="Start",
        is_final=False,
        created_at=now,
    )
    assert chunk.chunk_id == "custom-chunk-1"
    assert chunk.sequence_number == 0
    assert chunk.created_at == now


def test_stream_chunk_naive_datetime_assigned_utc() -> None:
    naive_dt = datetime(2026, 9, 27, 20, 0, 0)
    chunk = StreamChunk(
        chunk_id="chunk-utc",
        sequence_number=0,
        content="Test",
        created_at=naive_dt,
    )
    assert chunk.created_at.tzinfo == UTC


def test_stream_chunk_final_chunk_empty_content_allowed() -> None:
    chunk = StreamChunk.create(sequence_number=10, content="", is_final=True)
    assert chunk.is_final is True
    assert chunk.content == ""


def test_stream_chunk_negative_sequence_raises_value_error() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        StreamChunk.create(sequence_number=-1, content="Error")


def test_stream_chunk_empty_chunk_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="chunk_id no puede estar vacío"):
        StreamChunk(
            chunk_id="",
            sequence_number=0,
            content="Error",
        )


def test_stream_chunk_empty_content_non_final_raises_value_error() -> None:
    with pytest.raises(ValueError, match="no puede tener contenido vacío"):
        StreamChunk.create(sequence_number=0, content="", is_final=False)


def test_stream_chunk_immutability() -> None:
    chunk = StreamChunk.create(sequence_number=0, content="Test")
    with pytest.raises(AttributeError):
        chunk.content = "Nuevo"  # type: ignore[misc]


def test_stream_chunk_sequence_sorting() -> None:
    c3 = StreamChunk.create(sequence_number=3, content="!", is_final=True)
    c1 = StreamChunk.create(sequence_number=1, content="Hola ")
    c2 = StreamChunk.create(sequence_number=2, content="Mundo")

    chunks = [c3, c1, c2]
    sorted_chunks = sorted(chunks, key=lambda c: c.sequence_number)

    assert [c.sequence_number for c in sorted_chunks] == [1, 2, 3]
    assert "".join(c.content for c in sorted_chunks) == "Hola Mundo!"
