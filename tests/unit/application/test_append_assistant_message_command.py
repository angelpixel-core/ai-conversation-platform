"""Unit tests for AppendAssistantMessageCommand and AppendAssistantMessageCommandHandler (TDD)."""

from uuid import uuid4

import pytest

from src.application.conversations.commands.append_assistant_message import (
    AppendAssistantMessageCommand,
    AppendAssistantMessageCommandHandler,
    AppendAssistantMessageResult,
)
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.events.assistant_response_completed import (
    AssistantResponseCompletedDomainEvent,
)
from src.domain.conversations.events.message_appended import MessageAppendedDomainEvent
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.domain_error import DomainError
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_handle__valid_assistant_message__persists_message_and_commits() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("Hello AI")
    uow.conversations.add(conversation)
    uow.commit()

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="Hello! How can I help you today?",
    )

    # Act
    result = handler.handle(command)

    # Assert
    assert isinstance(result, AppendAssistantMessageResult)
    assert result.conversation_id == conversation.id
    assert result.role == MessageRole.ASSISTANT.value
    assert result.content == "Hello! How can I help you today?"
    assert result.created_at is not None
    assert uow._committed is True

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 2
    assert stored.messages[1].role == MessageRole.ASSISTANT
    assert stored.messages[1].content == "Hello! How can I help you today?"


def test_handle__valid_assistant_message__emits_domain_events() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("Tell me a fact")
    conversation.pull_events()  # Clear events recorded so far
    uow.conversations.add(conversation)

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="The Earth orbits the Sun.",
    )

    # Act
    handler.handle(command)

    # Assert
    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    events = stored.pull_events()
    assert len(events) == 2

    assert isinstance(events[0], MessageAppendedDomainEvent)
    assert events[0].conversation_id == conversation.id
    assert events[0].message.role == MessageRole.ASSISTANT
    assert events[0].message.content == "The Earth orbits the Sun."

    assert isinstance(events[1], AssistantResponseCompletedDomainEvent)
    assert events[1].conversation_id == conversation.id
    assert events[1].message.role == MessageRole.ASSISTANT
    assert events[1].message.content == "The Earth orbits the Sun."


def test_handle__conversation_not_found__raises_conversation_not_found_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    non_existent_id = uuid4()
    command = AppendAssistantMessageCommand(
        conversation_id=non_existent_id,
        content="Response to missing conversation",
    )

    # Act & Assert
    with pytest.raises(
        ConversationNotFoundError,
        match=f"Conversation {non_existent_id} not found",
    ):
        handler.handle(command)

    assert uow._committed is False


def test_handle__without_preceding_user_message__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Empty Conversation")
    uow.conversations.add(conversation)

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="Unprompted assistant answer",
    )

    # Act & Assert
    with pytest.raises(
        DomainError,
        match="Cannot append assistant message without a preceding user message",
    ):
        handler.handle(command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 0
    assert uow._committed is False


def test_handle__consecutive_assistant_messages__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("User question")
    uow.conversations.add(conversation)

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    first_command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="First answer",
    )
    second_command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="Second answer without user turn",
    )

    # Act
    handler.handle(first_command)

    # Act & Assert
    with pytest.raises(
        DomainError,
        match="Cannot append assistant message without a preceding user message",
    ):
        handler.handle(second_command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 2
    assert stored.messages[1].content == "First answer"


def test_handle__empty_content__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("User message")
    uow.conversations.add(conversation)

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="   ",
    )

    # Act & Assert
    with pytest.raises(DomainError, match="no puede estar vacío"):
        handler.handle(command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 1
    assert uow._committed is False


def test_handle__content_exceeds_max_length__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("User message")
    uow.conversations.add(conversation)

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="y" * 4001,
    )

    # Act & Assert
    with pytest.raises(DomainError, match="excede el límite máximo"):
        handler.handle(command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 1
    assert uow._committed is False


def test_handle__when_error_occurs__rolls_back_unit_of_work() -> None:
    # Arrange
    uow = InMemoryUnitOfWorkAdapter()
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("User message")
    uow.conversations.add(conversation)

    handler = AppendAssistantMessageCommandHandler(unit_of_work=uow)
    invalid_command = AppendAssistantMessageCommand(
        conversation_id=conversation.id,
        content="",
    )

    # Act & Assert
    with pytest.raises(DomainError):
        handler.handle(invalid_command)

    assert uow._committed is False
