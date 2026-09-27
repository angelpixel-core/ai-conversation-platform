"""Test template canónico para OutboxRelayService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import anyio
import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.infrastructure.persistence.mssql.models import OutboxMessageModel
from src.infrastructure.persistence.outbox.outbox_relay_service import (
    OutboxRelayService,
    default_topic_mapper,
)
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxStatus


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock(spec=MessageBrokerPort)
    broker.publish = AsyncMock()
    return broker


@pytest.mark.anyio
async def test_poll_and_publish_once_publishes_pending_message(
    in_memory_db, mock_broker: MagicMock
) -> None:
    msg_id = uuid4()
    with Session(in_memory_db) as session:
        msg = OutboxMessageModel(
            id=msg_id,
            event_type="MessageAppendedDomainEvent",
            payload='{"conversation_id": "c1", "content": "hi"}',
            status=OutboxStatus.PENDING.value,
            created_at=datetime.now(UTC),
        )
        session.add(msg)
        session.commit()

    relay = OutboxRelayService(
        session_factory=lambda: Session(in_memory_db),
        message_broker=mock_broker,
        batch_size=10,
    )

    published_count = await relay.poll_and_publish_once()

    assert published_count == 1
    mock_broker.publish.assert_called_once()
    call_args = mock_broker.publish.call_args
    topic = call_args[0][0]
    envelope = call_args[0][1]

    assert topic == "conversation.message.appended"
    assert envelope.id == msg_id
    assert envelope.event_type == "message_appended"
    assert envelope.payload == {"conversation_id": "c1", "content": "hi"}

    with Session(in_memory_db) as session:
        updated = session.get(OutboxMessageModel, msg_id)
        assert updated is not None
        assert updated.status == OutboxStatus.PUBLISHED.value
        assert updated.processed_at is not None


@pytest.mark.anyio
async def test_poll_and_publish_once_returns_zero_when_no_pending_messages(
    in_memory_db, mock_broker: MagicMock
) -> None:
    relay = OutboxRelayService(
        session_factory=lambda: Session(in_memory_db),
        message_broker=mock_broker,
        batch_size=10,
    )

    published_count = await relay.poll_and_publish_once()

    assert published_count == 0
    mock_broker.publish.assert_not_called()


@pytest.mark.anyio
async def test_poll_and_publish_once_marks_as_failed_on_broker_error(
    in_memory_db, mock_broker: MagicMock
) -> None:
    mock_broker.publish.side_effect = RuntimeError("RabbitMQ connection failure")

    msg_id = uuid4()
    with Session(in_memory_db) as session:
        msg = OutboxMessageModel(
            id=msg_id,
            event_type="MessageAppendedDomainEvent",
            payload='{"conversation_id": "c1"}',
            status=OutboxStatus.PENDING.value,
            created_at=datetime.now(UTC),
        )
        session.add(msg)
        session.commit()

    relay = OutboxRelayService(
        session_factory=lambda: Session(in_memory_db),
        message_broker=mock_broker,
        batch_size=10,
    )

    published_count = await relay.poll_and_publish_once()

    assert published_count == 0
    with Session(in_memory_db) as session:
        updated = session.get(OutboxMessageModel, msg_id)
        assert updated is not None
        assert updated.status == OutboxStatus.FAILED.value
        assert "RabbitMQ connection failure" in (updated.error_message or "")


@pytest.mark.anyio
async def test_outbox_relay_runs_and_stops_with_anyio(
    in_memory_db, mock_broker: MagicMock
) -> None:
    relay = OutboxRelayService(
        session_factory=lambda: Session(in_memory_db),
        message_broker=mock_broker,
        poll_interval=0.01,
    )

    async with anyio.create_task_group() as tg:
        tg.start_soon(relay.run)
        await anyio.sleep(0.05)
        relay.stop()


def test_default_topic_mapper() -> None:
    assert (
        default_topic_mapper("MessageAppendedDomainEvent")
        == "conversation.message.appended"
    )
    assert (
        default_topic_mapper("ConversationCreatedDomainEvent")
        == "conversation.created"
    )
    assert (
        default_topic_mapper("AssistantResponseCompletedDomainEvent")
        == "conversation.assistant.completed"
    )
    assert (
        default_topic_mapper("UserSessionTerminatedDomainEvent")
        == "conversation.user.session.terminated"
    )
