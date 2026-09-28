"""RabbitMQ topology configuration for secure tool execution events."""

from dataclasses import dataclass

from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)


@dataclass(frozen=True)
class ToolsTopologyConfig(RabbitMQTopologyConfig):
    """RabbitMQ topology configuration for async tool execution."""

    exchange_name: str = "ai_platform.tools"
    queue_name: str = "tools.execution.queue"
    dlx_exchange_name: str = "ai_platform.tools.dlx"
    dlq_name: str = "tools.execution.dlq"
    routing_key: str = "tools.execute"
    tenant_routing_pattern: str = "tenant.*.tools.execute"

    def format_tenant_routing_key(self, tenant_id: str, event_type: str = "tools.execute") -> str:
        """Generates tenant-scoped routing key: tenant.{tenant_id}.tools.{event_type}."""
        if event_type.startswith("tools."):
            return f"tenant.{tenant_id}.{event_type}"
        return f"tenant.{tenant_id}.tools.{event_type}"
