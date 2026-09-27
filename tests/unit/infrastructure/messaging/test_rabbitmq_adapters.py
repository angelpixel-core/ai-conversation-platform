"""Unit tests for RabbitMQ Publisher and Consumer Adapters (Infrastructure Layer)."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import aio_pika
import pytest

from src.application.shared.ports.event_consumer_port import EventConsumerPort
from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_publisher_adapter import (
    RabbitMQPublisherAdapter,
)


@pytest.fixture
def fake_connection_manager() -> MagicMock:
    """Fixture providing a mocked RabbitMQConnectionManager."""
    manager = MagicMock()
    fake_channel = MagicMock()
    fake_exchange = MagicMock()
    fake_queue = MagicMock()

    fake_channel.declare_exchange = AsyncMock(return_value=fake_exchange)
    fake_channel.declare_queue = AsyncMock(return_value=fake_queue)
    fake_channel.set_qos = AsyncMock()

    fake_exchange.publish = AsyncMock()
    fake_queue.consume = AsyncMock(return_value="test-consumer-tag")
    fake_queue.cancel = AsyncMock()

    manager.get_channel = AsyncMock(return_value=fake_channel)
    manager.fake_channel = fake_channel
    manager.fake_exchange = fake_exchange
    manager.fake_queue = fake_queue
    return manager


# ==============================================================================
# RabbitMQPublisherAdapter Tests
# ==============================================================================


@pytest.mark.anyio
async def test_publisher_implements_message_broker_port(
    fake_connection_manager: MagicMock,
) -> None:
    publisher = RabbitMQPublisherAdapter(
        connection_manager=fake_connection_manager,
        exchange_name="ai_platform.events",
    )
    assert isinstance(publisher, MessageBrokerPort)


@pytest.mark.anyio
async def test_publisher_serializes_and_publishes_event_envelope(
    fake_connection_manager: MagicMock,
) -> None:
    publisher = RabbitMQPublisherAdapter(
        connection_manager=fake_connection_manager,
        exchange_name="ai_platform.events",
    )

    corr_id = uuid4()
    envelope = EventEnvelope.create(
        event_type="conversation_created",
        payload={"conversation_id": "conv-123", "title": "Test"},
        correlation_id=corr_id,
    )

    await publisher.publish(topic="conversation.created", envelope=envelope)

    fake_connection_manager.get_channel.assert_called_once()
    fake_connection_manager.fake_channel.declare_exchange.assert_called_once_with(
        "ai_platform.events", type="topic", durable=True
    )

    fake_exchange = fake_connection_manager.fake_exchange
    fake_exchange.publish.assert_called_once()

    published_args = fake_exchange.publish.call_args
    message_arg: aio_pika.Message = published_args[0][0]
    routing_key_kwarg: str = published_args[1]["routing_key"]

    assert routing_key_kwarg == "conversation.created"
    assert isinstance(message_arg, aio_pika.Message)
    assert message_arg.content_type == "application/json"
    assert message_arg.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
    assert message_arg.message_id == str(envelope.id)
    assert message_arg.correlation_id == str(corr_id)
    assert message_arg.headers == {"event_type": "conversation_created"}

    deserialized_body = json.loads(message_arg.body.decode("utf-8"))
    assert deserialized_body["id"] == str(envelope.id)
    assert deserialized_body["event_type"] == "conversation_created"
    assert deserialized_body["payload"] == {"conversation_id": "conv-123", "title": "Test"}


@pytest.mark.anyio
async def test_publisher_handles_envelope_without_correlation_id(
    fake_connection_manager: MagicMock,
) -> None:
    publisher = RabbitMQPublisherAdapter(
        connection_manager=fake_connection_manager,
        exchange_name="ai_platform.events",
    )

    envelope = EventEnvelope.create(
        event_type="test_event",
        payload={"data": 42},
        correlation_id=None,
    )

    await publisher.publish(topic="test.topic", envelope=envelope)

    fake_exchange = fake_connection_manager.fake_exchange
    fake_exchange.publish.assert_called_once()
    message_arg: aio_pika.Message = fake_exchange.publish.call_args[0][0]

    assert message_arg.correlation_id is None


# ==============================================================================
# RabbitMQConsumerAdapter Tests
# ==============================================================================


@pytest.mark.anyio
async def test_consumer_implements_event_consumer_port(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
    )
    assert isinstance(consumer, EventConsumerPort)


@pytest.mark.anyio
async def test_consumer_subscribes_handlers(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
    )

    handler_called = False

    async def dummy_handler(env: EventEnvelope) -> None:
        nonlocal handler_called
        handler_called = True

    consumer.subscribe("conversation.message.appended", dummy_handler)
    assert dummy_handler in consumer._handlers.get("conversation.message.appended", [])


@pytest.mark.anyio
async def test_consumer_start_consuming_configures_qos_and_starts_consumer(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
        prefetch_count=5,
    )

    await consumer.start_consuming()

    fake_connection_manager.get_channel.assert_called_once()
    fake_connection_manager.fake_channel.set_qos.assert_called_once_with(prefetch_count=5)
    fake_connection_manager.fake_channel.declare_queue.assert_called_once_with(
        "conversation.llm_processing.queue", durable=True
    )
    fake_connection_manager.fake_queue.consume.assert_called_once()


@pytest.mark.anyio
async def test_consumer_dispatches_message_and_acks_on_success(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
    )

    received_envelopes: list[EventEnvelope] = []

    async def sample_handler(env: EventEnvelope) -> None:
        received_envelopes.append(env)

    consumer.subscribe("conversation.message.appended", sample_handler)

    test_env = EventEnvelope.create(
        event_type="message_appended",
        payload={"message_id": "msg-001", "content": "Hello!"},
    )

    fake_incoming_message = MagicMock()
    fake_incoming_message.body = json.dumps(test_env.to_dict()).encode("utf-8")
    fake_incoming_message.routing_key = "conversation.message.appended"
    fake_incoming_message.ack = AsyncMock()
    fake_incoming_message.reject = AsyncMock()

    await consumer._process_message(fake_incoming_message)

    assert len(received_envelopes) == 1
    assert received_envelopes[0].id == test_env.id
    assert received_envelopes[0].event_type == "message_appended"
    assert received_envelopes[0].payload == {"message_id": "msg-001", "content": "Hello!"}

    fake_incoming_message.ack.assert_called_once()
    fake_incoming_message.reject.assert_not_called()


@pytest.mark.anyio
async def test_consumer_rejects_malformed_json_message_to_dlq(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
    )

    fake_incoming_message = MagicMock()
    fake_incoming_message.body = b"not-a-valid-json{"
    fake_incoming_message.routing_key = "conversation.message.appended"
    fake_incoming_message.ack = AsyncMock()
    fake_incoming_message.reject = AsyncMock()

    await consumer._process_message(fake_incoming_message)

    fake_incoming_message.ack.assert_not_called()
    fake_incoming_message.reject.assert_called_once_with(requeue=False)


@pytest.mark.anyio
async def test_consumer_rejects_to_dlq_when_handler_raises_exception(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
    )

    async def failing_handler(env: EventEnvelope) -> None:
        raise RuntimeError("External service unavailable")

    consumer.subscribe("conversation.message.appended", failing_handler)

    test_env = EventEnvelope.create(
        event_type="message_appended",
        payload={"message_id": "msg-002"},
    )

    fake_incoming_message = MagicMock()
    fake_incoming_message.body = json.dumps(test_env.to_dict()).encode("utf-8")
    fake_incoming_message.routing_key = "conversation.message.appended"
    fake_incoming_message.ack = AsyncMock()
    fake_incoming_message.reject = AsyncMock()

    await consumer._process_message(fake_incoming_message)

    fake_incoming_message.ack.assert_not_called()
    fake_incoming_message.reject.assert_called_once_with(requeue=False)


@pytest.mark.anyio
async def test_consumer_stop_consuming_cancels_active_subscription(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="conversation.llm_processing.queue",
    )

    await consumer.start_consuming()
    await consumer.stop_consuming()

    fake_connection_manager.fake_queue.cancel.assert_called_once_with("test-consumer-tag")
    assert consumer._is_consuming is False


@pytest.mark.anyio
async def test_publisher_uses_get_exchange_when_passive(
    fake_connection_manager: MagicMock,
) -> None:
    publisher = RabbitMQPublisherAdapter(
        connection_manager=fake_connection_manager,
        exchange_name="ai_platform.events",
        passive=True,
    )
    fake_connection_manager.fake_channel.get_exchange = AsyncMock(
        return_value=fake_connection_manager.fake_exchange
    )
    envelope = EventEnvelope.create(event_type="test", payload={})
    await publisher.publish("test.topic", envelope)
    fake_connection_manager.fake_channel.get_exchange.assert_called_once_with(
        "ai_platform.events", ensure=False
    )


@pytest.mark.anyio
async def test_consumer_passes_queue_arguments_when_provided(
    fake_connection_manager: MagicMock,
) -> None:
    consumer = RabbitMQConsumerAdapter(
        connection_manager=fake_connection_manager,
        queue_name="test.queue",
        queue_arguments={"x-message-ttl": 60000},
    )
    await consumer.start_consuming()
    fake_connection_manager.fake_channel.declare_queue.assert_called_once_with(
        "test.queue", durable=True, arguments={"x-message-ttl": 60000}
    )
