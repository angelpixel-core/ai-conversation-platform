"""RabbitMQ message publisher adapter implementing MessageBrokerPort."""

import json
from typing import Any

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
        passive: bool = False,
    ) -> None:
        self.connection_manager = connection_manager
        self.exchange_name = exchange_name
        self.passive = passive

    async def publish(self, topic: str, envelope: EventEnvelope) -> None:
        """Publish an EventEnvelope to RabbitMQ.

        Args:
            topic: Routing key for the topic exchange.
            envelope: EventEnvelope containing metadata and event payload.
        """
        channel = await self.connection_manager.get_channel()
        if self.passive:
            exchange = await channel.get_exchange(self.exchange_name, ensure=False)
        else:
            exchange = await channel.declare_exchange(
                self.exchange_name,
                type="topic",
                durable=True,
            )

        headers: dict[str, Any] = {"event_type": envelope.event_type}
        if isinstance(envelope.payload, dict):
            trace_keys = {
                "traceparent",
                "tracestate",
                "x-trace-id",
                "x-span-id",
                "x_trace_id",
                "x_span_id",
            }
            for k in trace_keys:
                if k in envelope.payload:
                    headers[k] = str(envelope.payload[k])

        body_bytes = json.dumps(envelope.to_dict()).encode("utf-8")
        message = aio_pika.Message(
            body=body_bytes,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=str(envelope.id),
            correlation_id=str(envelope.correlation_id) if envelope.correlation_id else None,
            headers=headers,
        )

        await exchange.publish(message, routing_key=topic)
