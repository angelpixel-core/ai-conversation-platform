"""Test template canónico para LlmMessageProcessingWorker."""

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

    await worker.handle(envelope)

    with uow:
        updated = uow.conversations.get(active_conversation.id)
        assert updated is not None
        assert len(updated.messages) == 2
        last_msg = updated.messages[-1]
        assert last_msg.role == MessageRole.ASSISTANT
        assert last_msg.content == "Clean Architecture separates concern beautifully."
