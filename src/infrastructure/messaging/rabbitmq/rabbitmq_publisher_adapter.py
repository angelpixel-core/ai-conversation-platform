"""RabbitMQ message publisher adapter implementing MessageBrokerPort."""

import json

import aio_pika
from aio_pika import DeliveryMode

from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)


class RabbitMQPublisherAdapter(MessageBrokerPort):
    """Adapter for publishing EventEnvelope instances to RabbitMQ exchanges."""

    def __init__(
        self,
        connection_manager: RabbitMQConnectionManager,
        exchange_name: str = "ai_platform.events",
    ) -> None:
        self.connection_manager = connection_manager
        self.exchange_name = exchange_name

    async def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Publish an EventEnvelope to RabbitMQ.

        Args:
            topic: Routing key for the topic exchange.
            envelope: EventEnvelope containing metadata and event payload.
        """
        channel = await self.connection_manager.get_channel()
        exchange = await channel.declare_exchange(
            self.exchange_name,
            type="topic",
            durable=True,
        )

        body_bytes = json.dumps(envelope.to_dict()).encode("utf-8")
        message = aio_pika.Message(
            body=body_bytes,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=str(envelope.id),
            correlation_id=str(envelope.correlation_id) if envelope.correlation_id else None,
            headers={"event_type": envelope.event_type},
        )

        await exchange.publish(message, routing_key=topic)
