"""Unit tests for RabbitMQ Knowledge Topology Configuration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.messaging.rabbitmq.knowledge_topology_config import (
    KnowledgeTopologyConfig,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    TopologyDeclarationResult,
)


@pytest.mark.anyio
async def test_knowledge_topology_config_defaults() -> None:
    config = KnowledgeTopologyConfig()
    assert config.exchange_name == "ai_platform.knowledge_events"
    assert config.queue_name == "knowledge.indexing.queue"
    assert config.dlx_exchange_name == "ai_platform.knowledge_events.dlx"
    assert config.dlq_name == "knowledge.indexing.dlq"
    assert config.routing_key == "knowledge.document.uploaded"
    assert config.tenant_routing_pattern == "tenant.*.knowledge.document.uploaded"

    formatted = config.format_tenant_routing_key("acme-corp")
    assert formatted == "tenant.acme-corp.knowledge.document.uploaded"


@pytest.mark.anyio
async def test_knowledge_topology_declares_exchanges_and_queues() -> None:
    fake_channel = MagicMock()
    fake_main_exchange = MagicMock()
    fake_dlx_exchange = MagicMock()
    fake_main_queue = MagicMock()
    fake_dlq = MagicMock()

    fake_main_queue.bind = AsyncMock()
    fake_dlq.bind = AsyncMock()

    async def mock_declare_exchange(
        name: str, type: str = "direct", durable: bool = True, **kwargs
    ):
        if "dlx" in name:
            return fake_dlx_exchange
        return fake_main_exchange

    async def mock_declare_queue(
        name: str, durable: bool = True, arguments: dict | None = None, **kwargs
    ):
        if "dlq" in name:
            return fake_dlq
        return fake_main_queue

    fake_channel.declare_exchange = AsyncMock(side_effect=mock_declare_exchange)
    fake_channel.declare_queue = AsyncMock(side_effect=mock_declare_queue)

    config = KnowledgeTopologyConfig()
    result = await config.declare_topology(fake_channel)

    assert isinstance(result, TopologyDeclarationResult)
    assert result.exchange is fake_main_exchange
    assert result.queue is fake_main_queue
    assert result.dlx_exchange is fake_dlx_exchange
    assert result.dlq is fake_dlq

    # Verify DLQ and DLX declarations
    fake_channel.declare_exchange.assert_any_await(
        "ai_platform.knowledge_events.dlx",
        type="direct",
        durable=True,
    )
    fake_channel.declare_queue.assert_any_await(
        "knowledge.indexing.dlq",
        durable=True,
    )
    fake_dlq.bind.assert_awaited_once_with(
        fake_dlx_exchange,
        routing_key="knowledge.document.uploaded",
    )

    # Verify Main Exchange and Main Queue with DLQ arguments
    fake_channel.declare_exchange.assert_any_await(
        "ai_platform.knowledge_events",
        type="topic",
        durable=True,
    )
    fake_channel.declare_queue.assert_any_await(
        "knowledge.indexing.queue",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "ai_platform.knowledge_events.dlx",
            "x-dead-letter-routing-key": "knowledge.document.uploaded",
        },
    )
    fake_main_queue.bind.assert_any_await(
        fake_main_exchange,
        routing_key="knowledge.document.uploaded",
    )
    fake_main_queue.bind.assert_any_await(
        fake_main_exchange,
        routing_key="tenant.*.knowledge.document.uploaded",
    )
