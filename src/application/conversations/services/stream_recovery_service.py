"""StreamRecoveryService application service.

Rules:
- Belongs to src/application/conversations/services/.
- Orchestrates recovery and live forwarding of missed chunks for reconnected clients.
- Uses AnyIO for structured pauses, timeouts, and concurrency.
"""

import logging
from collections.abc import AsyncIterator

import anyio

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk

logger = logging.getLogger(__name__)


class StreamRecoveryService:
    """Application service to resume emission of interrupted streams."""

    def __init__(
        self,
        buffer_repo: StreamBufferRepositoryPort,
        poll_interval_seconds: float = 0.05,
        max_wait_seconds: float = 30.0,
    ) -> None:
        self._buffer_repo = buffer_repo
        self._poll_interval = poll_interval_seconds
        self._max_wait = max_wait_seconds

    @property
    def buffer_repo(self) -> StreamBufferRepositoryPort:
        """Expose the underlying StreamBufferRepositoryPort."""
        return self._buffer_repo

    async def get_buffered_tokens(self, stream_id: str) -> list[str]:
        """Retrieve already-buffered token chunks for a given stream."""
        chunks = await self._buffer_repo.get_chunks_since(
            stream_id=stream_id,
            since_sequence=-1,
        )
        return [c.content for c in chunks if c.content]

    async def recover_stream(
        self,
        stream_id: str,
        since_sequence: int = -1,
    ) -> AsyncIterator[StreamChunk]:
        """Asynchronous generator yielding unread chunks and live chunks until the stream
        completes.
        """
        current_seq = since_sequence
        elapsed = 0.0

        while True:
            # 1. Retrieve newly generated chunks
            new_chunks = await self._buffer_repo.get_chunks_since(
                stream_id=stream_id,
                since_sequence=current_seq,
            )

            for chunk in new_chunks:
                yield chunk
                current_seq = max(current_seq, chunk.sequence_number)
                elapsed = 0.0  # Reset timeout on activity

                if chunk.is_final:
                    logger.info(
                        "Stream %s completed its final transmission at sequence %d",
                        stream_id,
                        current_seq,
                    )
                    return

            # 2. If already completed without more pending chunks, terminate
            if await self._buffer_repo.is_stream_completed(stream_id):
                return

            # 3. Wait for the next batch with AnyIO
            await anyio.sleep(self._poll_interval)
            elapsed += self._poll_interval

            if elapsed >= self._max_wait:
                logger.warning(
                    "Timed out waiting for activity on stream %s after %ss",
                    stream_id,
                    self._max_wait,
                )
                break
