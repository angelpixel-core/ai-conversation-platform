"""Unit tests for MssqlOutboxRepositoryAdapter adapter."""

from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine

from src.infrastructure.persistence.mssql.outbox_repository import MssqlOutboxRepositoryAdapter
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage, OutboxStatus


def test_outbox_repository_save_and_get_pending() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppended",
        payload='{"text": "hi"}',
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        pending = repo.get_pending()

        assert len(pending) == 1
        assert pending[0].id == msg.id
        assert pending[0].event_type == "MessageAppended"
        assert pending[0].status == OutboxStatus.PENDING
        assert pending[0].payload == '{"text": "hi"}'


def test_outbox_repository_get_by_id() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="ConversationCreated",
        payload='{"title": "Test"}',
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        found = repo.get_by_id(msg.id)
        assert found is not None
        assert found.id == msg.id
        assert found.event_type == "ConversationCreated"

        assert repo.get_by_id(uuid4()) is None


def test_outbox_repository_mark_dispatched_and_failed() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    agg_id = uuid4()
    msg1 = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=agg_id,
        event_type="Evt1",
        payload="{}",
    )
    msg2 = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=agg_id,
        event_type="Evt2",
        payload="{}",
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg1)
        repo.save(msg2)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.mark_as_dispatched(msg1.id)
        repo.mark_as_failed(msg2.id, error="Broker unreachable")
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        pending = repo.get_pending()
        assert len(pending) == 0

        item1 = repo.get_by_id(msg1.id)
        assert item1 is not None
        assert item1.status == OutboxStatus.COMPLETED
        assert item1.processed_at is not None

        item2 = repo.get_by_id(msg2.id)
        assert item2 is not None
        assert item2.status == OutboxStatus.FAILED
        assert item2.error_message == "Broker unreachable"


def test_outbox_repository_save_updates_existing_message() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="Evt",
        payload="{}",
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg)
        session.commit()

    # Mutate message and re-save
    msg.mark_completed()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        loaded = repo.get_by_id(msg.id)
        assert loaded is not None
        assert loaded.status == OutboxStatus.COMPLETED


def test_outbox_repository_add_event_compatibility() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    class DummyEvent:
        def __str__(self) -> str:
            return '{"dummy": true}'

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.add(DummyEvent())
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        pending = repo.get_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "DummyEvent"


def test_outbox_repository_add_outbox_message_directly() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="DirectAdd",
        payload="{}",
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.add(msg)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        loaded = repo.get_by_id(msg.id)
        assert loaded is not None
        assert loaded.event_type == "DirectAdd"


def test_outbox_repository_mark_as_completed_alias() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="CompletedAlias",
        payload="{}",
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.mark_as_completed(msg.id)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        loaded = repo.get_by_id(msg.id)
        assert loaded is not None
        assert loaded.status == OutboxStatus.COMPLETED


def test_outbox_repository_mark_as_published() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="PublishedEvent",
        payload="{}",
    )

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.save(msg)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        repo.mark_as_published(msg.id)
        session.commit()

    with Session(engine) as session:
        repo = MssqlOutboxRepositoryAdapter(session=session)
        loaded = repo.get_by_id(msg.id)
        assert loaded is not None
        assert loaded.status == OutboxStatus.PUBLISHED
        assert loaded.processed_at is not None
