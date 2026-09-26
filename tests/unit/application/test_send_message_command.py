"""Unit tests for SendMessageCommand and SendMessageHandler (TDD)."""

from uuid import uuid4

import pytest

from src.application.conversations.commands.send_message import (
    SendMessageCommand,
    SendMessageHandler,
    SendMessageResult,
)
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.events.message_appended import MessageAppendedDomainEvent
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.domain_error import DomainError
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


def test_handle__valid_user_message__persists_message_and_commits() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    uow.conversations.add(conversation)
    uow.commit()

    handler = SendMessageHandler(unit_of_work=uow)
    command = SendMessageCommand(
        conversation_id=conversation.id,
        content="Hello, AI!",
    )

    # Act
    result = handler.handle(command)

    # Assert
    assert isinstance(result, SendMessageResult)
    assert result.conversation_id == conversation.id
    assert result.role == MessageRole.USER.value
    assert result.content == "Hello, AI!"
    assert result.created_at is not None
    assert uow._committed is True

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 1
    assert stored.messages[0].role == MessageRole.USER
    assert stored.messages[0].content == "Hello, AI!"


def test_handle__valid_user_message__emits_message_appended_domain_event() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    conversation.pull_events()  # Clear initial creation event
    uow.conversations.add(conversation)

    handler = SendMessageHandler(unit_of_work=uow)
    command = SendMessageCommand(
        conversation_id=conversation.id,
        content="Tell me a joke",
    )

    # Act
    handler.handle(command)

    # Assert
    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    events = stored.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], MessageAppendedDomainEvent)
    assert events[0].conversation_id == conversation.id
    assert events[0].message.content == "Tell me a joke"
    assert events[0].message.role == MessageRole.USER


def test_handle__conversation_not_found__raises_conversation_not_found_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    handler = SendMessageHandler(unit_of_work=uow)
    non_existent_id = uuid4()
    command = SendMessageCommand(
        conversation_id=non_existent_id,
        content="Hello in the void",
    )

    # Act & Assert
    with pytest.raises(
        ConversationNotFoundError,
        match=f"Conversation {non_existent_id} not found",
    ):
        handler.handle(command)

    assert uow._committed is False


def test_handle__empty_content__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    uow.conversations.add(conversation)

    handler = SendMessageHandler(unit_of_work=uow)
    command = SendMessageCommand(
        conversation_id=conversation.id,
        content="   ",
    )

    # Act & Assert
    with pytest.raises(DomainError, match="no puede estar vacío"):
        handler.handle(command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 0


def test_handle__content_exceeds_max_length__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    uow.conversations.add(conversation)

    handler = SendMessageHandler(unit_of_work=uow)
    command = SendMessageCommand(
        conversation_id=conversation.id,
        content="x" * 4001,
    )

    # Act & Assert
    with pytest.raises(DomainError, match="excede el límite máximo"):
        handler.handle(command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 0


def test_handle__consecutive_user_message__raises_domain_error() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    uow.conversations.add(conversation)

    handler = SendMessageHandler(unit_of_work=uow)
    first_command = SendMessageCommand(
        conversation_id=conversation.id,
        content="First message",
    )
    second_command = SendMessageCommand(
        conversation_id=conversation.id,
        content="Second message before assistant reply",
    )

    # Act
    handler.handle(first_command)

    # Act & Assert
    with pytest.raises(DomainError, match="Cannot append user message before assistant responds"):
        handler.handle(second_command)

    stored = uow.conversations.get(conversation.id)
    assert stored is not None
    assert len(stored.messages) == 1
    assert stored.messages[0].content == "First message"


def test_handle__when_error_occurs__rolls_back_unit_of_work() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create("Test Conversation")
    uow.conversations.add(conversation)

    handler = SendMessageHandler(unit_of_work=uow)
    invalid_command = SendMessageCommand(
        conversation_id=conversation.id,
        content="",
    )

    # Act & Assert
    with pytest.raises(DomainError):
        handler.handle(invalid_command)

    assert uow._committed is False
