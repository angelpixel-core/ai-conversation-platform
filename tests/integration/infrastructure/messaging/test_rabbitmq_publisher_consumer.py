"""Integration tests for RabbitMQ Publisher, Consumer and DLQ topology against real broker."""

import contextlib
import json
from uuid import uuid4

import anyio
import pytest

from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_publisher_adapter import (
    RabbitMQPublisherAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)


@pytest.mark.anyio
async def test_rabbitmq_e2e_publish_and_consume(
    rabbitmq_connection_manager: RabbitMQConnectionManager,
) -> None:
    suffix = uuid4().hex[:8]
    exchange_name = f"test.ai_platform.events.{suffix}"
    queue_name = f"test.conversation.queue.{suffix}"
    dlx_name = f"test.ai_platform.dlx.{suffix}"
    dlq_name = f"test.conversation.dlq.{suffix}"
    routing_key = f"test.conversation.message.appended.{suffix}"

    # Declare topology
    topology_config = RabbitMQTopologyConfig(
        exchange_name=exchange_name,
        queue_name=queue_name,
        dlx_exchange_name=dlx_name,
        dlq_name=dlq_name,
        routing_key=routing_key,
    )
    channel = await rabbitmq_connection_manager.get_channel()
    topology_result = await topology_config.declare_topology(channel)

    try:
        publisher = RabbitMQPublisherAdapter(
            connection_manager=rabbitmq_connection_manager,
            exchange_name=exchange_name,
        )
        consumer = RabbitMQConsumerAdapter(
            connection_manager=rabbitmq_connection_manager,
            queue_name=queue_name,
            prefetch_count=5,
            passive=True,
        )

        received_envelopes: list[EventEnvelope] = []
        received_event = anyio.Event()

        async def on_message_appended(env: EventEnvelope) -> None:
            received_envelopes.append(env)
            received_event.set()

        consumer.subscribe(routing_key, on_message_appended)
        await consumer.start_consuming()

        correlation_id = uuid4()
        envelope = EventEnvelope.create(
            event_type="message_appended",
            payload={"conversation_id": "conv-test", "content": "Hello real RabbitMQ!"},
            correlation_id=correlation_id,
        )

        await publisher.publish(topic=routing_key, envelope=envelope)

        with anyio.fail_after(5.0):
            await received_event.wait()

        assert len(received_envelopes) == 1
        received = received_envelopes[0]
        assert received.id == envelope.id
        assert received.event_type == "message_appended"
        assert received.payload == {
            "conversation_id": "conv-test",
            "content": "Hello real RabbitMQ!",
        }
        assert received.correlation_id == correlation_id

        await consumer.stop_consuming()
    finally:
        # Cleanup declared test entities
        await topology_result.queue.delete(if_empty=False, if_unused=False)
        await topology_result.dlq.delete(if_empty=False, if_unused=False)
        await topology_result.exchange.delete(if_unused=False)
        await topology_result.dlx_exchange.delete(if_unused=False)


@pytest.mark.anyio
async def test_rabbitmq_dlq_dead_lettering_on_handler_failure(
    rabbitmq_connection_manager: RabbitMQConnectionManager,
) -> None:
    suffix = uuid4().hex[:8]
    exchange_name = f"test.ai_platform.events.{suffix}"
    queue_name = f"test.conversation.queue.{suffix}"
    dlx_name = f"test.ai_platform.dlx.{suffix}"
    dlq_name = f"test.conversation.dlq.{suffix}"
    routing_key = f"test.conversation.message.appended.{suffix}"

    topology_config = RabbitMQTopologyConfig(
        exchange_name=exchange_name,
        queue_name=queue_name,
        dlx_exchange_name=dlx_name,
        dlq_name=dlq_name,
        routing_key=routing_key,
    )
    channel = await rabbitmq_connection_manager.get_channel()
    topology_result = await topology_config.declare_topology(channel)

    try:
        publisher = RabbitMQPublisherAdapter(
            connection_manager=rabbitmq_connection_manager,
            exchange_name=exchange_name,
        )
        consumer = RabbitMQConsumerAdapter(
            connection_manager=rabbitmq_connection_manager,
            queue_name=queue_name,
            prefetch_count=1,
            passive=True,
        )

        async def failing_handler(env: EventEnvelope) -> None:
            raise RuntimeError("Fatal downstream processing failure")

        consumer.subscribe(routing_key, failing_handler)
        await consumer.start_consuming()

        envelope = EventEnvelope.create(
            event_type="message_appended",
            payload={"error_test": True},
        )

        await publisher.publish(topic=routing_key, envelope=envelope)

        dlq = topology_result.dlq
        dlq_message = None
        for _ in range(50):
            with contextlib.suppress(Exception):
                dlq_message = await dlq.get(no_ack=False, fail=False)
                if dlq_message is not None:
                    break
            await anyio.sleep(0.1)

        assert dlq_message is not None
        await dlq_message.ack()

        dlq_payload = json.loads(dlq_message.body.decode("utf-8"))
        assert dlq_payload["id"] == str(envelope.id)
        assert dlq_payload["payload"] == {"error_test": True}

        await consumer.stop_consuming()
    finally:
        await topology_result.queue.delete(if_empty=False, if_unused=False)
        await topology_result.dlq.delete(if_empty=False, if_unused=False)
        await topology_result.exchange.delete(if_unused=False)
        await topology_result.dlx_exchange.delete(if_unused=False)
