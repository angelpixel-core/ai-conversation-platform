"""MSSQL Stream Buffer Repository adapter using SQLModel."""

from sqlmodel import Session, select

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.infrastructure.persistence.mssql.models import StreamBufferChunkModel


class MssqlStreamBufferRepository(StreamBufferRepositoryPort):
    """Relational adapter for stream buffer chunk persistence backed by SQLModel."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def append_chunk(self, stream_id: str, chunk: StreamChunk) -> None:
        model = StreamBufferChunkModel(
            id=chunk.chunk_id,
            stream_id=stream_id,
            sequence_number=chunk.sequence_number,
            content=chunk.content,
            is_final=chunk.is_final,
            created_at=chunk.created_at,
        )
        self._session.add(model)
        self._session.commit()

    async def get_chunks_since(self, stream_id: str, since_sequence: int) -> list[StreamChunk]:
        stmt = (
            select(StreamBufferChunkModel)
            .where(
                StreamBufferChunkModel.stream_id == stream_id,
                StreamBufferChunkModel.sequence_number > since_sequence,
            )
            .order_by(StreamBufferChunkModel.sequence_number.asc())  # type: ignore[attr-defined]
        )
        results = self._session.exec(stmt).all()
        return [
            StreamChunk(
                chunk_id=m.id,
                sequence_number=m.sequence_number,
                content=m.content,
                is_final=m.is_final,
                created_at=m.created_at,
            )
            for m in results
        ]

    async def is_stream_completed(self, stream_id: str) -> bool:
        stmt = select(StreamBufferChunkModel).where(
            StreamBufferChunkModel.stream_id == stream_id,
            StreamBufferChunkModel.is_final == True,  # noqa: E712
        )
        result = self._session.exec(stmt).first()
        return result is not None
