"""Unit tests for MessageBrokerPort and EventConsumerPort contracts (Application Layer)."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest

from src.application.shared.ports.event_consumer_port import EventConsumerPort
from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope


def test_cannot_instantiate_abstract_message_broker_port() -> None:
    # Act & Assert
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        MessageBrokerPort()  # type: ignore[abstract]


def test_cannot_instantiate_abstract_event_consumer_port() -> None:
    # Act & Assert
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        EventConsumerPort()  # type: ignore[abstract]


@pytest.mark.anyio
async def test_concrete_message_broker_port_publish() -> None:
    # Arrange
    class FakeMessageBroker(MessageBrokerPort):
        def __init__(self) -> None:
            self.published: list[tuple[str, EventEnvelope]] = []

        async def publish(self, topic: str, envelope: EventEnvelope) -> None:
            self.published.append((topic, envelope))

    broker = FakeMessageBroker()
    envelope = EventEnvelope.create(
        event_type="test.event.created",
        payload={"message": "hello broker"},
        correlation_id=uuid4(),
    )

    # Act
    await broker.publish("conversation.events", envelope)

    # Assert
    assert len(broker.published) == 1
    topic, pub_env = broker.published[0]
    assert topic == "conversation.events"
    assert pub_env == envelope


@pytest.mark.anyio
async def test_concrete_event_consumer_port_lifecycle_and_subscription() -> None:
    # Arrange
    class FakeConsumer(EventConsumerPort):
        def __init__(self) -> None:
            self.handlers: dict[str, list[Callable[[EventEnvelope], Awaitable[None]]]] = {}
            self.is_consuming: bool = False

        def subscribe(
            self,
            topic: str,
            handler: Callable[[EventEnvelope], Awaitable[None]],
        ) -> None:
            self.handlers.setdefault(topic, []).append(handler)

        async def start_consuming(self) -> None:
            self.is_consuming = True

        async def stop_consuming(self) -> None:
            self.is_consuming = False

    consumer = FakeConsumer()
    dispatched: list[EventEnvelope] = []

    async def sample_handler(envelope: EventEnvelope) -> None:
        dispatched.append(envelope)

    # Act - Subscribe
    consumer.subscribe("conversation.message.appended", sample_handler)

    # Assert - Subscription registered
    assert "conversation.message.appended" in consumer.handlers
    assert sample_handler in consumer.handlers["conversation.message.appended"]

    # Act - Start & Stop lifecycle
    assert consumer.is_consuming is False
    await consumer.start_consuming()
    assert consumer.is_consuming is True
    await consumer.stop_consuming()
    assert consumer.is_consuming is False

    # Simulate dispatching to handler
    test_envelope = EventEnvelope.create(
        event_type="conversation.message.appended",
        payload={"text": "hello"},
    )
    for handler in consumer.handlers["conversation.message.appended"]:
        await handler(test_envelope)

    assert len(dispatched) == 1
    assert dispatched[0] == test_envelope
