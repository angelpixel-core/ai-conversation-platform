"""Integration tests for OutboxRelayService concurrency against Microsoft SQL Server 2022."""

from datetime import UTC, datetime
from uuid import uuid4

import anyio
import pytest
from sqlalchemy.engine import Engine
from sqlmodel import select

from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.mssql.connection import create_session_factory
from src.infrastructure.persistence.mssql.models import OutboxMessageModel
from src.infrastructure.persistence.outbox.outbox_relay_service import (
    OutboxRelayService,
)
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxStatus


class ThreadSafeBrokerMock(MessageBrokerPort):
    """Thread-safe and task-safe mock broker recording published event IDs."""

    def __init__(self) -> None:
        self.published_ids: list[str] = []
        self._lock = anyio.Lock()

    async def publish(self, topic: str, envelope: EventEnvelope) -> None:
        async with self._lock:
            self.published_ids.append(str(envelope.id))


@pytest.mark.anyio
async def test_concurrent_outbox_relays_compete_without_duplicates(
    mssql_engine: Engine,
    clean_db: None,
) -> None:
    session_factory = create_session_factory(mssql_engine)
    total_messages = 20

    # 1. Pre-populate 20 pending outbox messages in SQL Server
    with session_factory() as session:
        for i in range(total_messages):
            msg = OutboxMessageModel(
                id=uuid4(),
                event_type="ConcurrencyTestDomainEvent",
                payload=f'{{"index": {i}, "content": "concurrency test"}}',
                status=OutboxStatus.PENDING.value,
                created_at=datetime.now(UTC),
            )
            session.add(msg)
        session.commit()

    broker = ThreadSafeBrokerMock()

    # 2. Spawn 3 concurrent OutboxRelayService instances
    relay_1 = OutboxRelayService(
        session_factory=session_factory,
        message_broker=broker,
        batch_size=5,
        poll_interval=0.01,
        event_types=["ConcurrencyTestDomainEvent"],
    )
    relay_2 = OutboxRelayService(
        session_factory=session_factory,
        message_broker=broker,
        batch_size=5,
        poll_interval=0.01,
        event_types=["ConcurrencyTestDomainEvent"],
    )
    relay_3 = OutboxRelayService(
        session_factory=session_factory,
        message_broker=broker,
        batch_size=5,
        poll_interval=0.01,
        event_types=["ConcurrencyTestDomainEvent"],
    )

    async def run_relay(relay: OutboxRelayService) -> None:
        while True:
            published = await relay.poll_and_publish_once()
            if published == 0:
                break
            await anyio.sleep(0.01)

    with anyio.fail_after(10.0):
        async with anyio.create_task_group() as tg:
            tg.start_soon(run_relay, relay_1)
            tg.start_soon(run_relay, relay_2)
            tg.start_soon(run_relay, relay_3)

    # 3. Assertions: exactly 20 published, zero duplicates!
    assert len(broker.published_ids) == total_messages
    assert len(set(broker.published_ids)) == total_messages

    # 4. Verify all records in SQL Server are marked PUBLISHED
    with session_factory() as session:
        records = session.exec(select(OutboxMessageModel)).all()
        assert len(records) == total_messages
        for r in records:
            assert r.status == OutboxStatus.PUBLISHED.value
            assert r.processed_at is not None
