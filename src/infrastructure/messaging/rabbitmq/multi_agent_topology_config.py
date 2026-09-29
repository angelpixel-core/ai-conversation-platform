"""RabbitMQ topology configuration for multi-agent delegation events."""

from dataclasses import dataclass
from typing import Any

from aio_pika.abc import AbstractChannel, AbstractRobustChannel

from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
    TopologyDeclarationResult,
)


@dataclass(frozen=True)
class MultiAgentTopologyConfig(RabbitMQTopologyConfig):
    """RabbitMQ topology configuration for async multi-agent subtask execution."""

    exchange_name: str = "ai_platform.agents"
    queue_name: str = "agent.specialist.queue"
    dlx_exchange_name: str = "ai_platform.agents.dlx"
    dlq_name: str = "agent.dead_letter.queue"
    routing_key: str = "agent.#"
    tenant_routing_pattern: str = "tenant.*.agent.#"
    queues: tuple[str, ...] = (
        "agent.supervisor.queue",
        "agent.specialist.queue",
        "agent.reviewer.queue",
    )

    def format_tenant_routing_key(self, tenant_id: str, event_type: str = "agent.#") -> str:
        """Generates tenant-scoped routing key: tenant.{tenant_id}.agent.{event_type}."""
        if event_type.startswith("agent."):
            return f"tenant.{tenant_id}.{event_type}"
        return f"tenant.{tenant_id}.agent.{event_type}"

    async def declare_topology(
        self,
        channel: AbstractChannel | AbstractRobustChannel | Any,
    ) -> TopologyDeclarationResult:
        """Idempotently declares Agent Topic exchange, Queues, DLX and DLQ with bindings."""
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

        exchange = await channel.declare_exchange(
            self.exchange_name,
            type="topic",
            durable=True,
        )

        declared_queues = []
        for q_name in self.queues:
            role_suffix = q_name.split(".")[1] if "." in q_name else "#"
            q = await channel.declare_queue(
                q_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": self.dlx_exchange_name,
                    "x-dead-letter-routing-key": self.routing_key,
                },
            )
            await q.bind(exchange, routing_key=f"agent.{role_suffix}.#")
            await q.bind(exchange, routing_key=f"tenant.*.agent.{role_suffix}.#")
            declared_queues.append(q)

        primary_queue = declared_queues[1] if len(declared_queues) > 1 else declared_queues[0]

        return TopologyDeclarationResult(
            exchange=exchange,
            queue=primary_queue,
            dlx_exchange=dlx_exchange,
            dlq=dlq,
        )
