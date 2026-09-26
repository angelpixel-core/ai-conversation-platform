from datetime import UTC, datetime

import pytest

from src.domain.conversations.value_objects.message import Message, MessageRole


def test_create_user_message_success() -> None:
    msg = Message.create_user_message("Hello AI assistant")

    assert msg.role == MessageRole.USER
    assert msg.content == "Hello AI assistant"
    assert isinstance(msg.created_at, datetime)
    assert msg.created_at.tzinfo is not None


def test_create_assistant_message_success() -> None:
    msg = Message.create_assistant_message("I am ready to help you.")

    assert msg.role == MessageRole.ASSISTANT
    assert msg.content == "I am ready to help you."


def test_create_system_message_success() -> None:
    msg = Message.create_system_message("You are a helpful AI assistant.")

    assert msg.role == MessageRole.SYSTEM
    assert msg.content == "You are a helpful AI assistant."


def test_message_equality_by_value() -> None:
    now = datetime.now(UTC)
    msg1 = Message(role=MessageRole.USER, content="Test content", created_at=now)
    msg2 = Message(role=MessageRole.USER, content="Test content", created_at=now)

    assert msg1 == msg2


def test_message_immutability() -> None:
    msg = Message.create_user_message("Original message")

    with pytest.raises(AttributeError):
        msg.content = "Mutated message"  # type: ignore[misc]


def test_message_validates_empty_content() -> None:
    with pytest.raises(ValueError, match="no puede estar vacío"):
        Message.create_user_message("   ")


def test_message_validates_max_length() -> None:
    too_long = "a" * 4001
    with pytest.raises(ValueError, match="excede el límite máximo"):
        Message.create_user_message(too_long)
