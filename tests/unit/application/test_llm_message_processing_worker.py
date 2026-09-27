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
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


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
