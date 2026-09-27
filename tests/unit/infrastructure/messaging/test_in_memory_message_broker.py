"""Unit tests for InMemoryMessageBroker adapter (Infrastructure Layer)."""

from uuid import uuid4

import pytest

from src.application.shared.ports.event_consumer_port import EventConsumerPort
from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBroker,
)


def test_in_memory_message_broker_implements_ports() -> None:
    broker = InMemoryMessageBroker()
    assert isinstance(broker, MessageBrokerPort)
    assert isinstance(broker, EventConsumerPort)


@pytest.mark.anyio
async def test_publish_and_consume_active_lifecycle() -> None:
    broker = InMemoryMessageBroker()
    received: list[EventEnvelope] = []

    async def message_handler(envelope: EventEnvelope) -> None:
        received.append(envelope)

    broker.subscribe("conversation.message.appended", message_handler)
    await broker.start_consuming()

    envelope = EventEnvelope.create(
        event_type="conversation.message.appended",
        payload={"text": "hello in memory"},
        correlation_id=uuid4(),
    )

    await broker.publish("conversation.message.appended", envelope)

    assert len(broker.published_messages) == 1
    assert broker.published_messages[0] == ("conversation.message.appended", envelope)
    assert len(received) == 1
    assert received[0] == envelope

    await broker.stop_consuming()


@pytest.mark.anyio
async def test_buffered_messages_dispatched_on_start_consuming() -> None:
    broker = InMemoryMessageBroker()
    received: list[EventEnvelope] = []

    async def message_handler(envelope: EventEnvelope) -> None:
        received.append(envelope)

    broker.subscribe("conversation.created", message_handler)

    envelope = EventEnvelope.create(
        event_type="conversation.created",
        payload={"id": "123"},
    )

    # Publish BEFORE consuming starts
    await broker.publish("conversation.created", envelope)

    # Handlers should not have received it yet
    assert len(received) == 0
    assert len(broker.published_messages) == 1

    # Start consuming should flush/dispatch buffered messages
    await broker.start_consuming()

    assert len(received) == 1
    assert received[0] == envelope

    await broker.stop_consuming()


@pytest.mark.anyio
async def test_multiple_handlers_for_same_topic() -> None:
    broker = InMemoryMessageBroker()
    handler1_calls: list[EventEnvelope] = []
    handler2_calls: list[EventEnvelope] = []

    async def handler1(envelope: EventEnvelope) -> None:
        handler1_calls.append(envelope)

    async def handler2(envelope: EventEnvelope) -> None:
        handler2_calls.append(envelope)

    broker.subscribe("user.registered", handler1)
    broker.subscribe("user.registered", handler2)
    await broker.start_consuming()

    envelope = EventEnvelope.create(
        event_type="user.registered",
        payload={"user_id": "u-1"},
    )
    await broker.publish("user.registered", envelope)

    assert len(handler1_calls) == 1
    assert len(handler2_calls) == 1
    assert handler1_calls[0] == envelope
    assert handler2_calls[0] == envelope

    await broker.stop_consuming()


@pytest.mark.anyio
async def test_different_topic_does_not_trigger_unsubscribed_handler() -> None:
    broker = InMemoryMessageBroker()
    received: list[EventEnvelope] = []

    async def handler(envelope: EventEnvelope) -> None:
        received.append(envelope)

    broker.subscribe("topic.a", handler)
    await broker.start_consuming()

    envelope = EventEnvelope.create(
        event_type="topic.b",
        payload={"data": 42},
    )
    await broker.publish("topic.b", envelope)

    assert len(received) == 0
    assert len(broker.published_messages) == 1

    await broker.stop_consuming()


@pytest.mark.anyio
async def test_clear_resets_broker_state() -> None:
    broker = InMemoryMessageBroker()
    envelope = EventEnvelope.create(
        event_type="test.event",
        payload={"foo": "bar"},
    )
    await broker.publish("test.topic", envelope)
    assert len(broker.published_messages) == 1

    broker.clear()
    assert len(broker.published_messages) == 0
    assert broker._is_consuming is False
    assert len(broker._handlers) == 0
