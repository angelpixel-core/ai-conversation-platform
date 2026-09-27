"""Unit tests for EventEnvelope Value Object (Domain Layer)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.domain.conversations.events.conversation_created import (
    ConversationCreatedDomainEvent,
)
from src.domain.shared.events.event_envelope import EventEnvelope


def test_create_event_envelope_defaults() -> None:
    # Arrange & Act
    envelope = EventEnvelope.create(
        event_type="test.event.created",
        payload={"key": "value"},
    )

    # Assert
    assert isinstance(envelope.id, UUID)
    assert envelope.event_type == "test.event.created"
    assert envelope.payload == {"key": "value"}
    assert envelope.correlation_id is None
    assert envelope.causation_id is None
    assert isinstance(envelope.occurred_on, datetime)
    assert envelope.occurred_on.tzinfo == UTC
    assert envelope.occurred_at == envelope.occurred_on


def test_create_event_envelope_with_explicit_values() -> None:
    # Arrange
    envelope_id = uuid4()
    correlation_id = uuid4()
    causation_id = uuid4()
    occurred_on = datetime(2026, 9, 26, 18, 0, 0, tzinfo=UTC)

    # Act
    envelope = EventEnvelope(
        id=envelope_id,
        event_type="conversation.message.appended",
        payload={"message": "hello"},
        correlation_id=correlation_id,
        causation_id=causation_id,
        occurred_on=occurred_on,
    )

    # Assert
    assert envelope.id == envelope_id
    assert envelope.event_type == "conversation.message.appended"
    assert envelope.payload == {"message": "hello"}
    assert envelope.correlation_id == correlation_id
    assert envelope.causation_id == causation_id
    assert envelope.occurred_on == occurred_on


def test_event_envelope_is_immutable() -> None:
    # Arrange
    envelope = EventEnvelope.create(
        event_type="test.event",
        payload={"key": "value"},
    )

    # Act & Assert
    with pytest.raises(FrozenInstanceError):
        envelope.event_type = "changed"  # type: ignore[misc]


def test_event_envelope_to_dict_and_from_dict_roundtrip() -> None:
    # Arrange
    correlation_id = uuid4()
    causation_id = uuid4()
    envelope = EventEnvelope.create(
        event_type="conversation.message.appended",
        payload={"turn": 1, "text": "test content"},
        correlation_id=correlation_id,
        causation_id=causation_id,
    )

    # Act
    data = envelope.to_dict()
    restored = EventEnvelope.from_dict(data)

    # Assert
    assert data["id"] == str(envelope.id)
    assert data["event_type"] == envelope.event_type
    assert data["payload"] == envelope.payload
    assert data["correlation_id"] == str(correlation_id)
    assert data["causation_id"] == str(causation_id)
    assert data["occurred_on"] == envelope.occurred_on.isoformat()

    assert restored.id == envelope.id
    assert restored.event_type == envelope.event_type
    assert restored.payload == envelope.payload
    assert restored.correlation_id == correlation_id
    assert restored.causation_id == causation_id
    assert restored.occurred_on == envelope.occurred_on


def test_event_envelope_from_domain_event() -> None:
    # Arrange
    conv_id = uuid4()
    domain_event = ConversationCreatedDomainEvent(
        conversation_id=conv_id,
    )
    correlation_id = uuid4()

    # Act
    envelope = EventEnvelope.from_domain_event(
        event=domain_event,
        correlation_id=correlation_id,
    )

    # Assert
    assert envelope.id == domain_event.event_id
    assert envelope.event_type == "conversation_created"
    assert envelope.payload == {
        "conversation_id": str(conv_id),
    }
    assert envelope.correlation_id == correlation_id
    assert envelope.occurred_on == domain_event.occurred_at


def test_event_envelope_from_nested_domain_event() -> None:
    # Arrange
    from src.domain.conversations.events.message_appended import MessageAppendedDomainEvent
    from src.domain.conversations.value_objects.message import Message, MessageRole

    conv_id = uuid4()
    now = datetime.now(UTC)
    msg = Message(role=MessageRole.USER, content="Hello world", created_at=now)
    event = MessageAppendedDomainEvent(conversation_id=conv_id, message=msg)

    # Act
    envelope = EventEnvelope.from_domain_event(event)

    # Assert
    assert envelope.id == event.event_id
    assert envelope.event_type == "message_appended"
    assert envelope.payload["conversation_id"] == str(conv_id)
    assert envelope.payload["message"]["content"] == "Hello world"
    assert envelope.payload["message"]["role"] == "user"
    assert envelope.payload["message"]["created_at"] == now.isoformat()


def test_event_envelope_from_dict_edge_cases() -> None:
    # Case 1: occurred_on is already a datetime object
    now = datetime.now(UTC)
    env1 = EventEnvelope.from_dict({"id": str(uuid4()), "occurred_on": now})
    assert env1.occurred_on == now

    # Case 2: occurred_on is missing -> defaults to now(UTC)
    env2 = EventEnvelope.from_dict({"id": str(uuid4())})
    assert isinstance(env2.occurred_on, datetime)
    assert env2.occurred_on.tzinfo == UTC

    # Case 3: payload with list of UUIDs or primitives
    item_id = uuid4()
    envelope = EventEnvelope.create(
        event_type="batch.created",
        payload={"items": [item_id, "item2"]},
    )
    serialized = envelope.to_dict()
    assert serialized["payload"]["items"] == [item_id, "item2"]


def test_event_envelope_from_domain_event_with_list() -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class BatchItemsDomainEvent:
        event_id: UUID
        items: list[Any]
        occurred_at: datetime

    now = datetime.now(UTC)
    u = uuid4()
    evt = BatchItemsDomainEvent(event_id=uuid4(), items=[u, now], occurred_at=now)
    env = EventEnvelope.from_domain_event(evt)

    assert env.payload["items"] == [str(u), now.isoformat()]
