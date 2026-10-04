"""RabbitMQ event consumer adapter implementing EventConsumerPort."""

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
        queue_arguments: dict[str, Any] | None = None,
        passive: bool = False,
    ) -> None:
        self.connection_manager = connection_manager
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.queue_arguments = queue_arguments
        self.passive = passive

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

        if self.passive:
            self._queue = await self._channel.get_queue(
                self.queue_name,
                ensure=False,
            )
        else:
            kwargs: dict[str, Any] = {}
            if self.queue_arguments is not None:
                kwargs["arguments"] = self.queue_arguments
            self._queue = await self._channel.declare_queue(
                self.queue_name,
                durable=True,
                **kwargs,
            )

        self._consumer_tag = await self._queue.consume(self._process_message)
        self._is_consuming = True

    async def _process_message(self, message: AbstractIncomingMessage | Any) -> None:
        """Process incoming message with resilient ack/dlq semantics.

        - If parsing or handler fails: message.reject(requeue=False) to route to DLQ.
        - If succeeds: message.ack().
        """
        try:
            body_dict = json.loads(message.body.decode("utf-8"))
            envelope = EventEnvelope.from_dict(body_dict)
            if hasattr(message, "headers") and message.headers:
                trace_keys = {
                    "traceparent",
                    "tracestate",
                    "x-trace-id",
                    "x-span-id",
                    "x_trace_id",
                    "x_span_id",
                }
                for k in trace_keys:
                    if (
                        k in message.headers
                        and isinstance(envelope.payload, dict)
                        and k not in envelope.payload
                    ):
                        envelope.payload[k] = message.headers[k]
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


__all__ = ["RabbitMQConsumerAdapter"]
