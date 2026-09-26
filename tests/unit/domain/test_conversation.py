import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.events.conversation_created import ConversationCreatedDomainEvent
from src.domain.conversations.events.message_appended import MessageAppendedDomainEvent
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.domain_error import DomainError


def test_create_conversation_normalizes_title() -> None:
    conversation = Conversation.create("  Support assistant  ")

    assert conversation.title == "Support assistant"


def test_create_conversation_rejects_empty_title() -> None:
    with pytest.raises(DomainError):
        Conversation.create("   ")


def test_create_conversation_records_created_event() -> None:
    conversation = Conversation.create("My new conversation")

    events = conversation.pull_events()
    assert len(events) == 1

    event = events[0]
    assert isinstance(event, ConversationCreatedDomainEvent)
    assert event.conversation_id == conversation.id
    assert event.event_id is not None
    assert event.occurred_at is not None


def test_append_user_message_success() -> None:
    conversation = Conversation.create("Messaging conversation")

    msg = conversation.append_user_message("What is Python?")

    assert len(conversation.messages) == 1
    assert conversation.messages[0].content == "What is Python?"
    assert conversation.messages[0].role == MessageRole.USER

    events = conversation.pull_events()
    # Pull includes ConversationCreatedDomainEvent and MessageAppendedDomainEvent
    assert len(events) == 2
    assert isinstance(events[1], MessageAppendedDomainEvent)
    assert events[1].message == msg


def test_append_assistant_message_success_after_user_message() -> None:
    conversation = Conversation.create("Turn conversation")
    conversation.append_user_message("Hello AI")

    msg = conversation.append_assistant_message("Hello! How can I help?")

    assert len(conversation.messages) == 2
    assert conversation.messages[1] == msg
    assert conversation.messages[1].role == MessageRole.ASSISTANT
    assert conversation.messages[1].content == "Hello! How can I help?"


def test_append_assistant_message_fails_without_preceding_user_message() -> None:
    conversation = Conversation.create("Empty conversation")

    with pytest.raises(DomainError, match="preceding user message"):
        conversation.append_assistant_message("Unsolicited response")


def test_append_user_message_fails_if_last_message_was_also_user() -> None:
    conversation = Conversation.create("Turn order conversation")
    conversation.append_user_message("First user question")

    with pytest.raises(DomainError, match="assistant responds"):
        conversation.append_user_message("Second user question without waiting")
