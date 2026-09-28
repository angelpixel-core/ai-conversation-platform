"""Unit tests for RabbitMQ Connection Manager and Topology Configuration (Infrastructure Layer)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
    TopologyDeclarationResult,
)


@pytest.mark.anyio
async def test_connection_manager_connects_and_caches() -> None:
    # Arrange
    fake_conn = MagicMock()
    fake_conn.is_closed = False
    fake_channel = AsyncMock()
    fake_conn.channel = AsyncMock(return_value=fake_channel)

    with patch(
        "src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager.aio_pika.connect_robust",
        new=AsyncMock(return_value=fake_conn),
    ) as mock_connect:
        manager = RabbitMQConnectionManager(url="amqp://guest:guest@localhost:5672/")

        # Act
        conn1 = await manager.get_connection()
        conn2 = await manager.get_connection()

        # Assert
        assert conn1 is fake_conn
        assert conn2 is fake_conn
        mock_connect.assert_awaited_once_with("amqp://guest:guest@localhost:5672/")

        # Test channel creation
        channel = await manager.get_channel()
        assert channel is fake_channel
        fake_conn.channel.assert_awaited_once()


@pytest.mark.anyio
async def test_connection_manager_reconnects_if_closed() -> None:
    # Arrange
    fake_conn1 = MagicMock()
    fake_conn1.is_closed = True
    fake_conn2 = MagicMock()
    fake_conn2.is_closed = False

    with patch(
        "src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager.aio_pika.connect_robust",
        new=AsyncMock(side_effect=[fake_conn1, fake_conn2]),
    ) as mock_connect:
        manager = RabbitMQConnectionManager(url="amqp://guest:guest@localhost:5672/")

        # Act
        conn1 = await manager.get_connection()
        assert conn1 is fake_conn1

        # Second call sees conn1.is_closed == True, so connects again
        conn2 = await manager.get_connection()
        assert conn2 is fake_conn2
        assert mock_connect.await_count == 2


@pytest.mark.anyio
async def test_connection_manager_close_lifecycle() -> None:
    # Arrange
    fake_conn = MagicMock()
    fake_conn.is_closed = False
    fake_conn.close = AsyncMock()

    with patch(
        "src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager.aio_pika.connect_robust",
        new=AsyncMock(return_value=fake_conn),
    ):
        manager = RabbitMQConnectionManager(url="amqp://guest:guest@localhost:5672/")
        await manager.get_connection()

        # Act
        await manager.close()

        # Assert
        fake_conn.close.assert_awaited_once()
        assert manager._connection is None


@pytest.mark.anyio
async def test_topology_config_declares_exchanges_queues_and_dlq() -> None:
    # Arrange
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

    config = RabbitMQTopologyConfig(
        exchange_name="ai_platform.events",
        queue_name="conversation.llm_processing.queue",
        dlx_exchange_name="ai_platform.events.dlx",
        dlq_name="conversation.llm_processing.dlq",
        routing_key="conversation.message.appended",
    )

    # Act
    result = await config.declare_topology(fake_channel)

    # Assert
    assert isinstance(result, TopologyDeclarationResult)
    assert result.exchange is fake_main_exchange
    assert result.queue is fake_main_queue
    assert result.dlx_exchange is fake_dlx_exchange
    assert result.dlq is fake_dlq

    # Check DLQ and DLX declarations
    fake_channel.declare_exchange.assert_any_await(
        "ai_platform.events.dlx",
        type="direct",
        durable=True,
    )
    fake_channel.declare_queue.assert_any_await(
        "conversation.llm_processing.dlq",
        durable=True,
    )
    fake_dlq.bind.assert_awaited_once_with(
        fake_dlx_exchange,
        routing_key="conversation.message.appended",
    )

    # Check Main Exchange and Main Queue declarations with DLQ arguments
    fake_channel.declare_exchange.assert_any_await(
        "ai_platform.events",
        type="topic",
        durable=True,
    )
    fake_channel.declare_queue.assert_any_await(
        "conversation.llm_processing.queue",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "ai_platform.events.dlx",
            "x-dead-letter-routing-key": "conversation.message.appended",
        },
    )
    fake_main_queue.bind.assert_any_await(
        fake_main_exchange,
        routing_key="conversation.message.appended",
    )
