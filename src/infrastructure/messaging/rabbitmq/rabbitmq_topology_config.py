"""RabbitMQ topology configuration declaring durable exchanges, queues and DLQ."""

from dataclasses import dataclass
from typing import Any

from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustChannel,
)


@dataclass(frozen=True)
class TopologyDeclarationResult:
    """Holds references to declared RabbitMQ entities."""

    exchange: AbstractExchange | Any
    queue: AbstractQueue | Any
    dlx_exchange: AbstractExchange | Any
    dlq: AbstractQueue | Any


@dataclass(frozen=True)
class RabbitMQTopologyConfig:
    """Declarative topology configuration for RabbitMQ event messaging."""

    exchange_name: str = "ai_platform.events"
    queue_name: str = "conversation.llm_processing.queue"
    dlx_exchange_name: str = "ai_platform.events.dlx"
    dlq_name: str = "conversation.llm_processing.dlq"
    routing_key: str = "conversation.message.appended"

    async def declare_topology(
        self,
        channel: AbstractChannel | AbstractRobustChannel | Any,
    ) -> TopologyDeclarationResult:
        """Idempotently declare Topic exchange, Main queue, DLX and DLQ with bindings.

        Args:
            channel: Active RabbitMQ channel.

        Returns:
            TopologyDeclarationResult: References to declared exchanges and queues.
        """
        # 1. Declare Dead-Letter Exchange (DLX) and Dead-Letter Queue (DLQ)
        dlx_exchange = await channel.declare_exchange(
            self.dlx_exchange_name,
            type="direct",
            durable=True,
        )
        dlq = await channel.declare_queue(
            self.dlq_name,
            durable=True,
        )
        await dlq.bind(dlx_exchange, routing_key=self.routing_key)

        # 2. Declare Main Topic Exchange and Queue with DLX arguments
        exchange = await channel.declare_exchange(
            self.exchange_name,
            type="topic",
            durable=True,
        )
        queue = await channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self.dlx_exchange_name,
                "x-dead-letter-routing-key": self.routing_key,
            },
        )
        await queue.bind(exchange, routing_key=self.routing_key)

        return TopologyDeclarationResult(
            exchange=exchange,
            queue=queue,
            dlx_exchange=dlx_exchange,
            dlq=dlq,
        )
