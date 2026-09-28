"""Integration tests for Worker with streaming buffer, audit, and idempotency."""

from collections.abc import AsyncIterator, Callable, Mapping, Sequence

import pytest
from sqlmodel import Session

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.application.shared.ports.idempotency_repository_port import IdempotencyStatus
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.mssql.audit_repository import MssqlAuditRepository
from src.infrastructure.persistence.mssql.idempotency_repository import (
    MssqlIdempotencyRepository,
)
from src.infrastructure.persistence.mssql.stream_buffer_repository import (
    MssqlStreamBufferRepository,
)
from src.infrastructure.persistence.mssql.unit_of_work import MssqlUnitOfWork


class RealStubLlmClient(LlmClientPort):
    """Stub LLM returning controlled tokens for integration tests."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.recorded_messages: list[Sequence[Mapping[str, str]]] = []

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        self.recorded_messages.append(messages)
        for token in self.tokens:
            yield token


@pytest.mark.anyio
async def test_worker_persists_streaming_buffer_and_audit_log_in_mssql(
    clean_db: None,
    mssql_session_factory: Callable[[], Session],
) -> None:
    # 1. Arrange: Create conversation in real MSSQL
    uow = MssqlUnitOfWork(session_factory=mssql_session_factory)
    conversation = Conversation.create(title="Streaming Buffer Worker Integration")
    conversation.append_user_message("Stream to buffer test")
    with uow:
        uow.conversations.add(conversation)
        uow.commit()

    # 2. Wire Worker with real MSSQL repositories backed by session factory
    stream_buffer_repo = MssqlStreamBufferRepository(session=mssql_session_factory)
    audit_repo = MssqlAuditRepository(session=mssql_session_factory)
    idempotency_repo = MssqlIdempotencyRepository(session=mssql_session_factory)
    llm = RealStubLlmClient(["Chunk A", ", ", "Chunk B."])

    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        stream_buffer_repo=stream_buffer_repo,
        audit_repo=audit_repo,
        idempotency_repo=idempotency_repo,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(conversation.id),
            "message": {
                "role": "user",
                "content": "Stream to buffer test",
            },
        },
    )

    # 3. Act: Worker handles event
    await worker.handle(envelope)

    # 4. Assert: Stream buffer chunks in real SQL Server
    chunks = await stream_buffer_repo.get_chunks_since(
        stream_id=str(conversation.id), since_sequence=0
    )
    assert len(chunks) == 4
    assert chunks[0].content == "Chunk A"
    assert chunks[0].sequence_number == 1
    assert chunks[0].is_final is False

    assert chunks[1].content == ", "
    assert chunks[1].sequence_number == 2

    assert chunks[2].content == "Chunk B."
    assert chunks[2].sequence_number == 3

    assert chunks[3].content == ""
    assert chunks[3].sequence_number == 4
    assert chunks[3].is_final is True
    assert await stream_buffer_repo.is_stream_completed(str(conversation.id)) is True

    # 5. Assert: Audit log entry in real SQL Server
    logs = await audit_repo.list_by_resource("conversation", str(conversation.id))
    assert len(logs) == 1
    audit = logs[0]
    assert audit.event_name == "llm_inference_completed"
    assert audit.actor_id == "worker:llm_message_processing_worker"
    assert audit.tokens_consumed == 3
    assert audit.payload["total_chunks"] == 3
    assert audit.payload["character_count"] == len("Chunk A, Chunk B.")

    # 6. Assert: Idempotency record in real SQL Server
    key = f"worker:event:{envelope.id}"
    record = await idempotency_repo.get(key)
    assert record is not None
    assert record.status == IdempotencyStatus.COMPLETED

    # 7. Assert: Conversation updated with assistant response in real SQL Server
    with uow:
        updated_conv = uow.conversations.get(conversation.id)
        assert updated_conv is not None
        assert len(updated_conv.messages) == 2
        assert updated_conv.messages[1].role == MessageRole.ASSISTANT
        assert updated_conv.messages[1].content == "Chunk A, Chunk B."

    # 8. Act & Assert: Duplicate delivery skips processing
    await worker.handle(envelope)
    assert len(llm.recorded_messages) == 1
    with uow:
        second_check = uow.conversations.get(conversation.id)
        assert second_check is not None
        assert len(second_check.messages) == 2
