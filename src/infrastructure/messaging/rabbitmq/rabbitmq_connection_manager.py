import logging

import aio_pika
import anyio
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

logger = logging.getLogger(__name__)


class RabbitMQConnectionManager:
    """Manages robust lifecycle, reconnection and channel acquisition for RabbitMQ."""

    def __init__(self, url: str = "amqp://guest:guest@localhost:5672/") -> None:
        self.url = url
        self._connection: AbstractRobustConnection | None = None

    async def get_connection(
        self, max_retries: int = 15, retry_delay: float = 2.0
    ) -> AbstractRobustConnection:
        """Acquire or reuse an open robust RabbitMQ connection with startup retry resilience."""
        if self._connection is None or self._connection.is_closed:
            for attempt in range(1, max_retries + 1):
                try:
                    self._connection = await aio_pika.connect_robust(self.url)
                    break
                except Exception as exc:
                    if attempt == max_retries:
                        logger.error(
                            "Failed to connect to RabbitMQ at %s after %d attempts: %s",
                            self.url,
                            max_retries,
                            exc,
                        )
                        raise
                    logger.warning(
                        "Waiting for RabbitMQ at %s (attempt %d/%d)...",
                        self.url,
                        attempt,
                        max_retries,
                    )
                    await anyio.sleep(retry_delay)
        if self._connection is None:
            raise RuntimeError(f"Could not connect to RabbitMQ at {self.url}")
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
