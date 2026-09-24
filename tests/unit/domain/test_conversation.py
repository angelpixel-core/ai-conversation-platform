import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.events.conversation_created import ConversationCreatedDomainEvent
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
