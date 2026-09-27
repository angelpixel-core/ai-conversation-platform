"""Template canónico para RabbitMQConsumerAdapter.

Reglas:
- Pertenece a src/infrastructure/messaging/rabbitmq/.
- Implementa EventConsumerPort.
- Configura QoS con prefetch_count.
- Soporta semántica ack en éxito y reject(requeue=False) ante fallas para desvío a DLQ.
"""

import json
import logging
from typing import Any

from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractQueue

from src.application.shared.ports.event_consumer_port import (
    EventConsumerPort,
    EventHandler,
)
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)

logger = logging.getLogger(__name__)


class RabbitMQConsumerAdapter(EventConsumerPort):
    """Adapter for subscribing handlers and consuming EventEnvelope instances from RabbitMQ."""

    def __init__(
        self,
        connection_manager: RabbitMQConnectionManager,
        queue_name: str = "conversation.llm_processing.queue",
        prefetch_count: int = 10,
    ) -> None:
        self.connection_manager = connection_manager
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count

        self._handlers: dict[str, list[EventHandler]] = {}
        self._is_consuming: bool = False
        self._channel: AbstractChannel | None = None
        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register an asynchronous handler for a designated topic / routing key."""
        self._handlers.setdefault(topic, []).append(handler)

    async def start_consuming(self) -> None:
        """Begin consuming messages from the RabbitMQ queue."""
        self._channel = await self.connection_manager.get_channel()
        await self._channel.set_qos(prefetch_count=self.prefetch_count)

        self._queue = await self._channel.declare_queue(
            self.queue_name,
            durable=True,
        )

        self._consumer_tag = await self._queue.consume(self._process_message)
        self._is_consuming = True

    async def _process_message(self, message: AbstractIncomingMessage | Any) -> None:
        """Process incoming message with resilient ack/dlq semantics."""
        try:
            body_dict = json.loads(message.body.decode("utf-8"))
            envelope = EventEnvelope.from_dict(body_dict)
        except Exception:
            logger.exception("Failed to deserialize RabbitMQ message. Rejecting to DLQ.")
            await message.reject(requeue=False)
            return

        routing_key = getattr(message, "routing_key", "") or ""
        handlers = self._handlers.get(routing_key, [])

        try:
            for handler in handlers:
                await handler(envelope)
            await message.ack()
        except Exception:
            logger.exception(
                "Handler failed while processing event %s. Rejecting to DLQ.",
                envelope.id,
            )
            await message.reject(requeue=False)

    async def stop_consuming(self) -> None:
        """Gracefully stop consuming messages and cancel queue subscription."""
        if self._is_consuming and self._queue is not None and self._consumer_tag is not None:
            await self._queue.cancel(self._consumer_tag)

        self._is_consuming = False
        self._consumer_tag = None
