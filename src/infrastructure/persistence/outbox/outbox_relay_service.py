"""Outbox Relay Service for transactional polling and reliable publishing to Event Broker."""

import json
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import anyio
from sqlmodel import Session, select

from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.mssql.models import OutboxMessageModel
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxStatus

logger = logging.getLogger(__name__)


def _to_snake_case(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def default_topic_mapper(event_type: str) -> str:
    """Map internal domain event type names to AMQP topic routing keys."""
    clean_name = event_type
    if clean_name.endswith("DomainEvent"):
        clean_name = clean_name[: -len("DomainEvent")]

    if clean_name == "MessageAppended":
        return "conversation.message.appended"
    if clean_name == "ConversationCreated":
        return "conversation.created"
    if clean_name == "AssistantResponseCompleted":
        return "conversation.assistant.completed"

    snake = _to_snake_case(clean_name).replace("_", ".")
    return f"conversation.{snake}"


class OutboxRelayService:
    """Autonomous transactional poller that relays pending outbox messages to RabbitMQ."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        message_broker: MessageBrokerPort,
        batch_size: int = 10,
        poll_interval: float = 0.5,
        topic_mapper: Callable[[str], str] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.message_broker = message_broker
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.topic_mapper = topic_mapper or default_topic_mapper
        self._is_running: bool = False

    async def poll_and_publish_once(self) -> int:
        """Fetch pending outbox messages with locking hints, publish, and mark as published.

        Returns:
            int: Number of successfully dispatched messages.
        """
        with self.session_factory() as session:
            # Table locking hint WITH (UPDLOCK, READPAST) for SQL Server concurrency,
            # which is ignored cleanly on dialects like SQLite.
            stmt = (
                select(OutboxMessageModel)
                .with_hint(OutboxMessageModel, "WITH (UPDLOCK, READPAST)", "mssql")
                .where(OutboxMessageModel.status == OutboxStatus.PENDING.value)
                .order_by(OutboxMessageModel.created_at, OutboxMessageModel.id)  # type: ignore[arg-type]
                .limit(self.batch_size)
            )
            messages = session.exec(stmt).all()
            if not messages:
                session.rollback()
                return 0

            dispatched_count = 0
            for msg in messages:
                try:
                    payload_data: Any
                    try:
                        payload_data = json.loads(msg.payload)
                    except Exception:
                        payload_data = {"raw_payload": msg.payload}

                    clean_type = msg.event_type
                    if clean_type.endswith("DomainEvent"):
                        clean_type = clean_type[: -len("DomainEvent")]

                    if (
                        isinstance(payload_data, dict)
                        and "event_type" in payload_data
                        and "payload" in payload_data
                    ):
                        envelope = EventEnvelope.from_dict(payload_data)
                    else:
                        event_type_name = _to_snake_case(clean_type)
                        envelope = EventEnvelope.create(
                            event_type=event_type_name,
                            payload=payload_data
                            if isinstance(payload_data, dict)
                            else {"data": payload_data},
                            envelope_id=msg.id,
                        )

                    topic = self.topic_mapper(msg.event_type)
                    await self.message_broker.publish(topic, envelope)

                    msg.status = OutboxStatus.PUBLISHED.value
                    msg.processed_at = datetime.now(UTC)
                    session.add(msg)
                    session.commit()
                    dispatched_count += 1
                except Exception as exc:
                    logger.exception("Error relaying outbox message %s: %s", msg.id, exc)
                    session.rollback()
                    msg.status = OutboxStatus.FAILED.value
                    msg.error_message = str(exc)
                    session.add(msg)
                    session.commit()

            return dispatched_count

    async def run(self) -> None:
        """Run the polling loop continuously until stopped."""
        self._is_running = True
        while self._is_running:
            try:
                count = await self.poll_and_publish_once()
                if count == 0:
                    await anyio.sleep(self.poll_interval)
            except anyio.get_cancelled_exc_class():
                break
            except Exception as exc:
                logger.warning("Outbox relay polling encountered transient error: %s", exc)
                await anyio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Signal the polling loop to stop gracefully."""
        self._is_running = False
