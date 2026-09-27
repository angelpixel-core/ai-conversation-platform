"""Test template canónico para StreamChunk Value Object."""

import pytest

from .stream_chunk import StreamChunk


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


def test_stream_chunk_final_chunk_empty_content_allowed() -> None:
    chunk = StreamChunk.create(sequence_number=10, content="", is_final=True)
    assert chunk.is_final is True
    assert chunk.content == ""


def test_stream_chunk_negative_sequence_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        StreamChunk.create(sequence_number=-1, content="Error")


def test_stream_chunk_empty_content_non_final_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede tener contenido vacío"):
        StreamChunk.create(sequence_number=0, content="", is_final=False)


def test_stream_chunk_immutability() -> None:
    chunk = StreamChunk.create(sequence_number=0, content="Test")
    with pytest.raises(AttributeError):
        chunk.content = "Nuevo"  # type: ignore[misc]
