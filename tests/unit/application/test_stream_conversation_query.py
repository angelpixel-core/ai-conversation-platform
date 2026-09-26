"""Unit tests for StreamConversationQuery and StreamConversationQueryHandler (TDD)."""

from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any
from uuid import uuid4

import pytest

from src.application.conversations.queries.stream_conversation import (
    StreamConversationQuery,
    StreamConversationQueryHandler,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.shared.domain_error import DomainError
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


class FakeStreamingLlmClient(LlmClientPort):
    """Fake LLM Client that records calls and returns predetermined token streams."""

    def __init__(self, tokens_to_yield: list[str] | None = None) -> None:
        self.tokens_to_yield = (
            tokens_to_yield if tokens_to_yield is not None else ["AI", " response"]
        )
        self.recorded_calls: list[dict[str, Any]] = []

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        self.recorded_calls.append(
            {
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        for token in self.tokens_to_yield:
            yield token


@pytest.mark.anyio
async def test_handle__valid_query__streams_tokens_from_llm() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("What is Python?")
    uow.conversations.add(conversation)

    llm_client = FakeStreamingLlmClient(tokens_to_yield=["Python", " is", " great!"])
    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm_client,
    )
    query = StreamConversationQuery(conversation_id=conversation.id)

    # Act
    token_stream = await handler.handle(query)
    tokens = [token async for token in token_stream]

    # Assert
    assert tokens == ["Python", " is", " great!"]
    assert len(llm_client.recorded_calls) == 1
    call = llm_client.recorded_calls[0]
    assert call["messages"] == [{"role": "user", "content": "What is Python?"}]
    assert call["temperature"] == 0.7
    assert call["max_tokens"] == 1000


@pytest.mark.anyio
async def test_handle__multi_turn_conversation__sends_full_history_to_llm() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Dialogue")
    conversation.append_user_message("Turn 1 User")
    conversation.append_assistant_message("Turn 1 Assistant")
    conversation.append_user_message("Turn 2 User")
    uow.conversations.add(conversation)

    llm_client = FakeStreamingLlmClient()
    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm_client,
    )
    query = StreamConversationQuery(conversation_id=conversation.id)

    # Act
    stream = await handler.handle(query)
    _ = [t async for t in stream]

    # Assert
    assert len(llm_client.recorded_calls) == 1
    call = llm_client.recorded_calls[0]
    assert call["messages"] == [
        {"role": "user", "content": "Turn 1 User"},
        {"role": "assistant", "content": "Turn 1 Assistant"},
        {"role": "user", "content": "Turn 2 User"},
    ]


@pytest.mark.anyio
async def test_handle__custom_temperature_and_max_tokens__passes_parameters_to_llm() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Custom Parameters")
    conversation.append_user_message("Tell me something")
    uow.conversations.add(conversation)

    llm_client = FakeStreamingLlmClient()
    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm_client,
    )
    query = StreamConversationQuery(
        conversation_id=conversation.id,
        temperature=0.2,
        max_tokens=500,
    )

    # Act
    stream = await handler.handle(query)
    _ = [t async for t in stream]

    # Assert
    assert len(llm_client.recorded_calls) == 1
    call = llm_client.recorded_calls[0]
    assert call["temperature"] == 0.2
    assert call["max_tokens"] == 500


@pytest.mark.anyio
async def test_handle__conversation_not_found__raises_conversation_not_found_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    llm_client = FakeStreamingLlmClient()
    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm_client,
    )
    non_existent_id = uuid4()
    query = StreamConversationQuery(conversation_id=non_existent_id)

    # Act & Assert
    with pytest.raises(
        ConversationNotFoundError,
        match=f"Conversation {non_existent_id} not found",
    ):
        await handler.handle(query)


@pytest.mark.anyio
async def test_handle__conversation_without_messages__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Empty Conversation")
    uow.conversations.add(conversation)

    llm_client = FakeStreamingLlmClient()
    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm_client,
    )
    query = StreamConversationQuery(conversation_id=conversation.id)

    # Act & Assert
    with pytest.raises(
        DomainError,
        match="Cannot stream response for a conversation with no messages",
    ):
        await handler.handle(query)


@pytest.mark.anyio
async def test_handle__last_message_not_from_user__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Conversation with reply")
    conversation.append_user_message("User prompt")
    conversation.append_assistant_message("Assistant answered")
    uow.conversations.add(conversation)

    llm_client = FakeStreamingLlmClient()
    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm_client,
    )
    query = StreamConversationQuery(conversation_id=conversation.id)

    # Act & Assert
    with pytest.raises(
        DomainError,
        match="Cannot stream response when the last message is not from user",
    ):
        await handler.handle(query)


def test_query__temperature_out_of_bounds__raises_value_error() -> None:
    with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
        StreamConversationQuery(conversation_id=uuid4(), temperature=-0.1)

    with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
        StreamConversationQuery(conversation_id=uuid4(), temperature=2.1)


def test_query__invalid_max_tokens__raises_value_error() -> None:
    with pytest.raises(ValueError, match="Max tokens must be greater than 0"):
        StreamConversationQuery(conversation_id=uuid4(), max_tokens=0)

    with pytest.raises(ValueError, match="Max tokens must be greater than 0"):
        StreamConversationQuery(conversation_id=uuid4(), max_tokens=-5)


@pytest.mark.anyio
async def test_handler_initialized_with_unit_of_work() -> None:
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("UOW Init")
    conversation.append_user_message("Hello")
    uow.conversations.add(conversation)

    llm_client = FakeStreamingLlmClient()
    handler = StreamConversationQueryHandler(
        unit_of_work=uow,
        llm_client=llm_client,
    )
    query = StreamConversationQuery(conversation_id=conversation.id)

    stream = await handler.handle(query)
    tokens = [t async for t in stream]
    assert len(tokens) == 2


def test_handler_initialization_errors() -> None:
    llm_client = FakeStreamingLlmClient()
    uow = InMemoryUnitOfWork()

    with pytest.raises(ValueError, match="Either conversation_repository or unit_of_work"):
        StreamConversationQueryHandler(llm_client=llm_client)

    with pytest.raises(ValueError, match="llm_client must be provided"):
        StreamConversationQueryHandler(conversation_repository=uow.conversations)


@pytest.mark.anyio
async def test_handle_supports_coroutine_returning_stream() -> None:
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Coroutine Stream")
    conversation.append_user_message("Hello")
    uow.conversations.add(conversation)

    class CoroutineLlmClient(LlmClientPort):
        async def stream_chat(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            messages: Sequence[Mapping[str, str]],
            temperature: float = 0.7,
            max_tokens: int = 1000,
        ) -> AsyncIterator[str]:  # type: ignore[override]
            async def token_gen() -> AsyncIterator[str]:
                yield "Async"
                yield " Coroutine"

            return token_gen()

    handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=CoroutineLlmClient(),
    )
    query = StreamConversationQuery(conversation_id=conversation.id)

    stream = await handler.handle(query)
    tokens = [t async for t in stream]
    assert tokens == ["Async", " Coroutine"]
