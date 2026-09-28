"""RabbitMQ topology configuration for knowledge document ingestion events."""

from dataclasses import dataclass

from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)


@dataclass(frozen=True)
class KnowledgeTopologyConfig(RabbitMQTopologyConfig):
    """RabbitMQ topology configuration for knowledge document indexing."""

    exchange_name: str = "ai_platform.knowledge_events"
    queue_name: str = "knowledge.indexing.queue"
    dlx_exchange_name: str = "ai_platform.knowledge_events.dlx"
    dlq_name: str = "knowledge.indexing.dlq"
    routing_key: str = "knowledge.document.uploaded"
    tenant_routing_pattern: str = "tenant.*.knowledge.document.uploaded"

    def format_tenant_routing_key(
        self, tenant_id: str, event_type: str = "knowledge.document.uploaded"
    ) -> str:
        """Generates tenant-scoped routing key: tenant.{tenant_id}.{event_type}."""
        return f"tenant.{tenant_id}.{event_type}"
