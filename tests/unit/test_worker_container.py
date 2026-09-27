"""Unit tests for worker container composition root and lifecycle wiring."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBroker,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.infrastructure.persistence.mssql.unit_of_work import MssqlUnitOfWork
from src.infrastructure.shared.config.settings import (
    MessagingDriver,
    PersistenceDriver,
    Settings,
)
from src.worker_container import WorkerContainer, create_worker_container


def test_create_worker_container_default_wires_in_memory() -> None:
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY,
        MESSAGING_DRIVER=MessagingDriver.IN_MEMORY,
    )
    container = create_worker_container(settings=settings)

    assert isinstance(container, WorkerContainer)
    assert isinstance(container.unit_of_work, InMemoryUnitOfWork)
    assert isinstance(container.consumer, InMemoryMessageBroker)
    assert isinstance(container.worker_handler, LlmMessageProcessingWorker)


def test_create_worker_container_with_mssql_driver() -> None:
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.MSSQL,
        DATABASE_URL="sqlite:///:memory:",
        MESSAGING_DRIVER=MessagingDriver.IN_MEMORY,
    )
    container = create_worker_container(settings=settings)

    assert isinstance(container, WorkerContainer)
    assert isinstance(container.unit_of_work, MssqlUnitOfWork)


def test_create_worker_container_with_rabbitmq_driver() -> None:
    mock_conn = MagicMock(spec=RabbitMQConnectionManager)
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY,
        MESSAGING_DRIVER=MessagingDriver.RABBITMQ,
    )
    container = create_worker_container(
        settings=settings,
        connection_manager=mock_conn,
    )

    assert isinstance(container, WorkerContainer)
    assert isinstance(container.consumer, RabbitMQConsumerAdapter)
    assert container.connection_manager is mock_conn


def test_create_worker_container_with_custom_uow_and_llm() -> None:
    custom_uow = InMemoryUnitOfWork()
    custom_llm = MagicMock()
    container = create_worker_container(
        unit_of_work=custom_uow,
        llm_client=custom_llm,
    )
    assert container.unit_of_work is custom_uow
    assert container.llm_client is custom_llm


def test_create_worker_container_rabbitmq_default_conn_mgr() -> None:
    settings = Settings(
        MESSAGING_DRIVER=MessagingDriver.RABBITMQ,
    )
    container = create_worker_container(settings=settings)
    assert isinstance(container.consumer, RabbitMQConsumerAdapter)
    assert container.connection_manager is not None


@pytest.mark.anyio
async def test_worker_container_start_and_stop_lifecycle_in_memory() -> None:
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY,
        MESSAGING_DRIVER=MessagingDriver.IN_MEMORY,
    )
    container = create_worker_container(settings=settings)

    assert isinstance(container.consumer, InMemoryMessageBroker)
    await container.start()
    assert container.consumer._is_consuming is True

    await container.stop()
    assert container.consumer._is_consuming is False


@pytest.mark.anyio
async def test_worker_container_start_and_stop_lifecycle_rabbitmq() -> None:
    mock_conn = MagicMock(spec=RabbitMQConnectionManager)
    mock_channel = AsyncMock()
    mock_conn.get_channel = AsyncMock(return_value=mock_channel)
    mock_conn.close = AsyncMock()

    mock_topo = MagicMock(spec=RabbitMQTopologyConfig)
    mock_topo.declare_topology = AsyncMock()
    mock_topo.routing_key = "conversation.message.appended"

    mock_consumer = MagicMock(spec=RabbitMQConsumerAdapter)
    mock_consumer.start_consuming = AsyncMock()
    mock_consumer.stop_consuming = AsyncMock()
    mock_consumer.subscribe = MagicMock()

    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY,
        MESSAGING_DRIVER=MessagingDriver.RABBITMQ,
    )
    container = create_worker_container(
        settings=settings,
        consumer=mock_consumer,
        connection_manager=mock_conn,
        topology_config=mock_topo,
    )

    await container.start()
    mock_conn.get_channel.assert_awaited_once()
    mock_topo.declare_topology.assert_awaited_once_with(mock_channel)
    mock_consumer.start_consuming.assert_awaited_once()

    await container.stop()
    mock_consumer.stop_consuming.assert_awaited_once()
    mock_conn.close.assert_awaited_once()
