"""RabbitMQ connection manager providing resilient and robust connections."""

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractRobustConnection


class RabbitMQConnectionManager:
    """Manages robust lifecycle, reconnection and channel acquisition for RabbitMQ."""

    def __init__(self, url: str = "amqp://guest:guest@localhost:5672/") -> None:
        self.url = url
        self._connection: AbstractRobustConnection | None = None

    async def get_connection(self) -> AbstractRobustConnection:
        """Acquire or reuse an open robust RabbitMQ connection."""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self.url)
        return self._connection

    async def get_channel(self) -> AbstractChannel:
        """Acquire a new robust channel from the active connection."""
        conn = await self.get_connection()
        return await conn.channel()

    async def close(self) -> None:
        """Gracefully close the active RabbitMQ connection."""
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
