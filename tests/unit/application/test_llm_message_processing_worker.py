"""Unit tests for LlmMessageProcessingWorker (Application Layer - TDD Red Phase)."""

from collections.abc import AsyncIterator, Mapping, Sequence
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.application.conversations.commands.append_assistant_message import (
    AppendAssistantMessageHandler,
)
from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.application.shared.ports.idempotency_repository_port import IdempotencyStatus
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.in_memory import (
    InMemoryAuditRepositoryAdapter,
    InMemoryIdempotencyRepositoryAdapter,
    InMemoryStreamBufferRepositoryAdapter,
    InMemoryUnitOfWork,
)


class StubLlmClient(LlmClientPort):
    """Stub LLM client producing predefined token streams."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens if tokens is not None else ["Hello", ", ", "I am your AI assistant."]
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


class ErrorLlmClient(LlmClientPort):
    """Failing LLM client to verify error propagation to DLQ."""

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        raise RuntimeError("LLM provider unavailable: 503 service overloaded")
        yield ""  # pragma: no cover


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def active_conversation(uow: InMemoryUnitOfWork) -> Conversation:
    conversation = Conversation.create(title="Support Session")
    conversation.append_user_message("What is Clean Architecture?")
    uow.conversations.add(conversation)
    uow.commit()
    return conversation


@pytest.mark.anyio
async def test_worker_processes_user_message_and_appends_assistant_response(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["Clean Architecture", " separates concern", " beautifully."])
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {
                "role": "user",
                "content": "What is Clean Architecture?",
            },
        },
    )

    # Act
    await worker.handle(envelope)

    # Assert
    assert len(llm.recorded_messages) == 1
    prompt_history = llm.recorded_messages[0]
    assert len(prompt_history) == 1
    assert prompt_history[0]["role"] == "user"
    assert prompt_history[0]["content"] == "What is Clean Architecture?"

    # Verify assistant message was persisted via UoW
    with uow:
        updated = uow.conversations.get(active_conversation.id)
        assert updated is not None
        assert len(updated.messages) == 2
        last_msg = updated.messages[-1]
        assert last_msg.role == MessageRole.ASSISTANT
        assert last_msg.content == "Clean Architecture separates concern beautifully."


@pytest.mark.anyio
async def test_worker_can_be_invoked_as_callable(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["Response via __call__"])
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)

    envelope = EventEnvelope.create(
        event_type="message_appended",
        payload={
            "conversation_id": str(active_conversation.id),
            "role": "user",
            "content": "What is Clean Architecture?",
        },
    )

    # Act
    await worker(envelope)

    # Assert
    with uow:
        updated = uow.conversations.get(active_conversation.id)
        assert updated is not None
        assert len(updated.messages) == 2
        assert updated.messages[-1].content == "Response via __call__"


@pytest.mark.anyio
async def test_worker_ignores_assistant_messages_to_prevent_infinite_loops(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["This should never be generated"])
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {
                "role": "assistant",
                "content": "Already an assistant response",
            },
        },
    )

    # Act
    await worker.handle(envelope)

    # Assert: LLM was never called, no messages appended
    assert len(llm.recorded_messages) == 0
    with uow:
        updated = uow.conversations.get(active_conversation.id)
        assert updated is not None
        assert len(updated.messages) == 1


@pytest.mark.anyio
async def test_worker_raises_on_missing_conversation_id(uow: InMemoryUnitOfWork) -> None:
    # Arrange
    llm = StubLlmClient()
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={"message": {"role": "user", "content": "No conv id"}},
    )

    # Act & Assert
    with pytest.raises(ValueError, match="conversation_id"):
        await worker.handle(envelope)


@pytest.mark.anyio
async def test_worker_raises_conversation_not_found(uow: InMemoryUnitOfWork) -> None:
    # Arrange
    llm = StubLlmClient()
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)
    non_existent_id = uuid4()

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(non_existent_id),
            "message": {"role": "user", "content": "Hello"},
        },
    )

    # Act & Assert
    with pytest.raises(ConversationNotFoundError):
        await worker.handle(envelope)


@pytest.mark.anyio
async def test_worker_propagates_llm_failure_for_dlq_routing(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = ErrorLlmClient()
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {"role": "user", "content": "Trigger error"},
        },
    )

    # Act & Assert: Exception propagates so RabbitMQConsumerAdapter can reject to DLQ
    with pytest.raises(RuntimeError, match="LLM provider unavailable"):
        await worker.handle(envelope)


@pytest.mark.anyio
async def test_worker_allows_custom_append_assistant_message_handler(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["Custom handler output"])
    custom_handler = MagicMock(spec=AppendAssistantMessageHandler)
    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        append_handler=custom_handler,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {"role": "user", "content": "Hello"},
        },
    )

    # Act
    await worker.handle(envelope)

    # Assert
    assert custom_handler.handle.called
    call_arg = custom_handler.handle.call_args[0][0]
    assert call_arg.conversation_id == active_conversation.id
    assert call_arg.content == "Custom handler output"


@pytest.mark.anyio
async def test_worker_buffers_chunks_incrementally_to_stream_buffer_repo(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["Chunk 1", ", ", "Chunk 2"])
    buffer_repo = InMemoryStreamBufferRepositoryAdapter()
    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        stream_buffer_repo=buffer_repo,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {"role": "user", "content": "Buffer test"},
        },
    )

    # Act
    await worker.handle(envelope)

    # Assert: Chunks buffered with sequential numbering and final chunk marker
    chunks = await buffer_repo.get_chunks_since(
        stream_id=str(active_conversation.id), since_sequence=0
    )
    assert len(chunks) == 4  # 3 tokens + 1 final chunk
    assert chunks[0].sequence_number == 1
    assert chunks[0].content == "Chunk 1"
    assert chunks[0].is_final is False

    assert chunks[1].sequence_number == 2
    assert chunks[1].content == ", "
    assert chunks[1].is_final is False

    assert chunks[2].sequence_number == 3
    assert chunks[2].content == "Chunk 2"
    assert chunks[2].is_final is False

    assert chunks[3].sequence_number == 4
    assert chunks[3].is_final is True
    assert await buffer_repo.is_stream_completed(str(active_conversation.id)) is True


@pytest.mark.anyio
async def test_worker_records_audit_log_upon_completion(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["Audit", " token", " response"])
    audit_repo = InMemoryAuditRepositoryAdapter()
    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        audit_repo=audit_repo,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {"role": "user", "content": "Audit this"},
        },
    )

    # Act
    await worker.handle(envelope)

    # Assert
    records = await audit_repo.list_by_resource("conversation", str(active_conversation.id))
    assert len(records) == 1
    record = records[0]
    assert record.event_name == "llm_inference_completed"
    assert record.actor_id == "worker:llm_message_processing_worker"
    assert record.resource_type == "conversation"
    assert record.resource_id == str(active_conversation.id)
    assert record.action == "chat_completion"
    assert record.tokens_consumed == 3
    assert record.payload["total_chunks"] == 3
    assert record.payload["character_count"] == len("Audit token response")


@pytest.mark.anyio
async def test_worker_respects_amqp_idempotency_and_skips_duplicates(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = StubLlmClient(["Once only"])
    idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        idempotency_repo=idempotency_repo,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {"role": "user", "content": "Idempotent msg"},
        },
    )

    # Act 1: Initial handling
    await worker.handle(envelope)

    # Assert 1: Completed and recorded
    key = f"worker:event:{envelope.id}"
    rec = await idempotency_repo.get(key)
    assert rec is not None
    assert rec.status == IdempotencyStatus.COMPLETED
    assert len(llm.recorded_messages) == 1

    with uow:
        conv = uow.conversations.get(active_conversation.id)
        assert conv is not None
        assert len(conv.messages) == 2

    # Act 2: Duplicate delivery of identical AMQP message
    await worker.handle(envelope)

    # Assert 2: LLM not called again, no duplicate message in conversation
    assert len(llm.recorded_messages) == 1
    with uow:
        conv = uow.conversations.get(active_conversation.id)
        assert conv is not None
        assert len(conv.messages) == 2


@pytest.mark.anyio
async def test_worker_marks_idempotency_failed_when_llm_raises_error(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # Arrange
    llm = ErrorLlmClient()
    idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        idempotency_repo=idempotency_repo,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "message": {"role": "user", "content": "Trigger failure"},
        },
    )

    # Act & Assert
    with pytest.raises(RuntimeError, match="LLM provider unavailable"):
        await worker.handle(envelope)

    key = f"worker:event:{envelope.id}"
    rec = await idempotency_repo.get(key)
    assert rec is not None
    assert rec.status == IdempotencyStatus.FAILED

