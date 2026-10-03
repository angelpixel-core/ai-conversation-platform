"""Integration test configuration and fixtures for RabbitMQ real broker testing."""

import os
from collections.abc import AsyncGenerator

import aio_pika
import pytest

from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)

BROKER_TEST_URL = os.getenv(
    "BROKER_URL",
    "amqp://guest:guest@localhost:5672/",
)
RABBITMQ_TEST_URL = BROKER_TEST_URL


@pytest.fixture
async def rabbitmq_connection_manager() -> AsyncGenerator[RabbitMQConnectionManager, None]:
    """Provide a real RabbitMQConnectionManager if RabbitMQ is reachable, else skip."""
    try:
        conn = await aio_pika.connect_robust(BROKER_TEST_URL, timeout=3.0)
        await conn.close()
    except Exception as exc:
        pytest.skip(f"RabbitMQ broker not reachable at {BROKER_TEST_URL}: {exc}")

    manager = RabbitMQConnectionManager(url=BROKER_TEST_URL)
    yield manager
    await manager.close()
