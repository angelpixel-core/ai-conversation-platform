"""Integration tests for MssqlOutboxRepository against live SQL Server 2022."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.engine import Engine

from src.infrastructure.persistence.mssql.connection import create_session_factory
from src.infrastructure.persistence.mssql.outbox_repository import MssqlOutboxRepository
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage, OutboxStatus


def test_mssql_outbox_full_lifecycle(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)

    msg1 = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="ConversationCreated",
        payload='{"order": 1}',
    )
    msg2 = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppended",
        payload='{"order": 2}',
    )
    msg2.created_at = msg1.created_at + timedelta(seconds=1)

    # 1. Insert outbox records
    with session_factory() as session:
        repo = MssqlOutboxRepository(session=session)
        repo.save(msg1)
        repo.save(msg2)
        session.commit()

    # 2. Fetch pending messages
    with session_factory() as session:
        repo = MssqlOutboxRepository(session=session)
        pending = repo.get_pending()
        assert len(pending) == 2
        assert pending[0].id == msg1.id
        assert pending[1].id == msg2.id

    # 3. Mark msg1 dispatched, msg2 failed
    with session_factory() as session:
        repo = MssqlOutboxRepository(session=session)
        repo.mark_as_dispatched(msg1.id)
        repo.mark_as_failed(msg2.id, error="Transient network glitch")
        session.commit()

    # 4. Verify in subsequent session
    with session_factory() as session:
        repo = MssqlOutboxRepository(session=session)
        pending_after = repo.get_pending()
        assert len(pending_after) == 0

        item1 = repo.get_by_id(msg1.id)
        assert item1 is not None
        assert item1.status == OutboxStatus.COMPLETED
        assert item1.processed_at is not None

        item2 = repo.get_by_id(msg2.id)
        assert item2 is not None
        assert item2.status == OutboxStatus.FAILED
        assert item2.error_message == "Transient network glitch"
