"""Unit tests for Conversation messaging domain logic and invariants (TDD - RED)."""

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.events.assistant_response_completed import (
    AssistantResponseCompletedDomainEvent,
)
from src.domain.conversations.events.message_appended import MessageAppendedDomainEvent
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.domain_error import DomainError


def test_append_user_message_success() -> None:
    conversation = Conversation.create("Test Conversation")
    conversation.pull_events()  # Clear ConversationCreated event

    user_msg = conversation.append_user_message("Hello AI")

    assert len(conversation.messages) == 1
    assert conversation.messages[0] == user_msg
    assert user_msg.role == MessageRole.USER
    assert user_msg.content == "Hello AI"

    events = conversation.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], MessageAppendedDomainEvent)
    assert events[0].conversation_id == conversation.id
    assert events[0].message == user_msg


def test_append_user_message_fails_on_consecutive_user_messages() -> None:
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("First user message")

    with pytest.raises(DomainError, match="Cannot append user message before assistant responds"):
        conversation.append_user_message("Second user message")


def test_append_user_message_fails_on_empty_content() -> None:
    conversation = Conversation.create("Test Conversation")

    with pytest.raises(DomainError, match="no puede estar vacío"):
        conversation.append_user_message("   ")


def test_append_user_message_fails_on_overly_long_content() -> None:
    conversation = Conversation.create("Test Conversation")
    too_long = "x" * 4001

    with pytest.raises(DomainError, match="excede el límite máximo"):
        conversation.append_user_message(too_long)


def test_append_assistant_message_success() -> None:
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("User prompt")
    conversation.pull_events()  # Clear previous events

    assistant_msg = conversation.append_assistant_message("Assistant response")

    assert len(conversation.messages) == 2
    assert conversation.messages[1] == assistant_msg
    assert assistant_msg.role == MessageRole.ASSISTANT
    assert assistant_msg.content == "Assistant response"

    events = conversation.pull_events()
    assert len(events) == 2
    assert isinstance(events[0], MessageAppendedDomainEvent)
    assert events[0].message == assistant_msg
    assert isinstance(events[1], AssistantResponseCompletedDomainEvent)
    assert events[1].message == assistant_msg
    assert events[1].conversation_id == conversation.id


def test_append_assistant_message_fails_without_preceding_user_message() -> None:
    conversation = Conversation.create("Test Conversation")

    with pytest.raises(
        DomainError, match="Cannot append assistant message without a preceding user message"
    ):
        conversation.append_assistant_message("Unsolicited assistant message")


def test_append_assistant_message_fails_on_empty_content() -> None:
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("User question")

    with pytest.raises(DomainError, match="no puede estar vacío"):
        conversation.append_assistant_message("")


def test_multi_turn_conversation_flow() -> None:
    conversation = Conversation.create("Multi-turn")

    conversation.append_user_message("Turn 1 User")
    conversation.append_assistant_message("Turn 1 Assistant")
    conversation.append_user_message("Turn 2 User")
    conversation.append_assistant_message("Turn 2 Assistant")

    assert len(conversation.messages) == 4
    assert [m.content for m in conversation.messages] == [
        "Turn 1 User",
        "Turn 1 Assistant",
        "Turn 2 User",
        "Turn 2 Assistant",
    ]
    assert [m.role for m in conversation.messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]


def test_messages_property_is_immutable_tuple() -> None:
    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("Hello")

    messages = conversation.messages
    assert isinstance(messages, tuple)
