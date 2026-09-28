"""Resume stream query handler."""

from collections.abc import AsyncIterator

from src.application.conversations.queries.resume_stream_query import (
    ResumeStreamQuery,
)
from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk


class ResumeStreamQueryHandler:
    """Application use case for orchestrating stream recovery for reconnected clients."""

    def __init__(self, recovery_service: StreamRecoveryService) -> None:
        self._recovery_service = recovery_service

    async def handle(self, query: ResumeStreamQuery) -> AsyncIterator[StreamChunk]:
        """Handles stream resumption by delegating to StreamRecoveryService."""
        since_seq = query.last_event_id if query.last_event_id is not None else -1
        async for chunk in self._recovery_service.recover_stream(
            stream_id=query.stream_id,
            since_sequence=since_seq,
        ):
            yield chunk
