"""Test template canónico para RabbitMQ Connection Manager y Topology Configuration."""

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
async def test_connection_manager_acquires_and_reuses_robust_connection() -> None:
    manager = RabbitMQConnectionManager(url="amqp://test:test@rabbitmq:5672/")

    fake_conn = MagicMock()
    fake_conn.is_closed = False

    with patch(
        "aio_pika.connect_robust", new_callable=AsyncMock, return_value=fake_conn
    ) as mock_connect:
        conn1 = await manager.get_connection()
        conn2 = await manager.get_connection()

        assert conn1 is fake_conn
        assert conn2 is fake_conn
        mock_connect.assert_called_once_with("amqp://test:test@rabbitmq:5672/")


@pytest.mark.anyio
async def test_connection_manager_reconnects_when_closed() -> None:
    manager = RabbitMQConnectionManager(url="amqp://test:test@rabbitmq:5672/")

    closed_conn = MagicMock()
    closed_conn.is_closed = True

    new_conn = MagicMock()
    new_conn.is_closed = False

    with patch(
        "aio_pika.connect_robust",
        new_callable=AsyncMock,
        side_effect=[closed_conn, new_conn],
    ) as mock_connect:
        first_call = await manager.get_connection()
        assert first_call is closed_conn

        second_call = await manager.get_connection()
        assert second_call is new_conn
        assert mock_connect.call_count == 2


@pytest.mark.anyio
async def test_connection_manager_acquires_channel_and_closes() -> None:
    manager = RabbitMQConnectionManager()

    fake_channel = MagicMock()
    fake_conn = MagicMock()
    fake_conn.is_closed = False
    fake_conn.channel = AsyncMock(return_value=fake_channel)
    fake_conn.close = AsyncMock()

    with patch(
        "aio_pika.connect_robust", new_callable=AsyncMock, return_value=fake_conn
    ):
        ch = await manager.get_channel()
        assert ch is fake_channel
        fake_conn.channel.assert_called_once()

        await manager.close()
        fake_conn.close.assert_called_once()

        # Second close should be idempotent
        await manager.close()
        assert fake_conn.close.call_count == 1


@pytest.mark.anyio
async def test_topology_config_declares_exchanges_queues_and_dlq() -> None:
    config = RabbitMQTopologyConfig(
        exchange_name="ai_platform.events",
        queue_name="conversation.llm_processing.queue",
        dlx_exchange_name="ai_platform.events.dlx",
        dlq_name="conversation.llm_processing.dlq",
        routing_key="conversation.message.appended",
    )

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

    result = await config.declare_topology(fake_channel)

    assert isinstance(result, TopologyDeclarationResult)
    assert result.exchange is fake_main_exchange
    assert result.queue is fake_main_queue
    assert result.dlx_exchange is fake_dlx_exchange
    assert result.dlq is fake_dlq

    # Assert DLX declared as direct & durable
    fake_channel.declare_exchange.assert_any_call(
        "ai_platform.events.dlx", type="direct", durable=True
    )
    # Assert Main exchange declared as topic & durable
    fake_channel.declare_exchange.assert_any_call(
        "ai_platform.events", type="topic", durable=True
    )

    # Assert DLQ declared durable
    fake_channel.declare_queue.assert_any_call(
        "conversation.llm_processing.dlq", durable=True
    )
    # Assert Main queue declared with DLX configuration
    fake_channel.declare_queue.assert_any_call(
        "conversation.llm_processing.queue",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "ai_platform.events.dlx",
            "x-dead-letter-routing-key": "conversation.message.appended",
        },
    )

    # Assert bindings
    fake_dlq.bind.assert_called_once_with(
        fake_dlx_exchange, routing_key="conversation.message.appended"
    )
    fake_main_queue.bind.assert_called_once_with(
        fake_main_exchange, routing_key="conversation.message.appended"
    )
