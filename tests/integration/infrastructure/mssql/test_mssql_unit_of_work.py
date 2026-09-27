"""Integration tests for MssqlUnitOfWork against live SQL Server 2022."""

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import select

from src.domain.conversations.entities.conversation import Conversation
from src.infrastructure.persistence.mssql.connection import create_session_factory
from src.infrastructure.persistence.mssql.models import ConversationModel, OutboxMessageModel
from src.infrastructure.persistence.mssql.unit_of_work import MssqlUnitOfWork
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage


def test_mssql_uow_atomic_commit(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)
    uow = MssqlUnitOfWork(session_factory=session_factory)

    conversation = Conversation.create(title="Integration UoW Commit")
    conversation.append_user_message("UoW User Msg")
    outbox = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=conversation.id,
        event_type="ConversationCreated",
        payload='{"title": "Integration UoW Commit"}',
    )

    with uow:
        uow.conversations.add(conversation)
        uow.outbox.save(outbox)
        uow.commit()

    with session_factory() as session:
        saved_conv = session.get(ConversationModel, conversation.id)
        saved_outbox = session.get(OutboxMessageModel, outbox.id)

        assert saved_conv is not None
        assert saved_conv.title == "Integration UoW Commit"
        assert len(saved_conv.messages) == 1
        assert saved_conv.messages[0].content == "UoW User Msg"

        assert saved_outbox is not None
        assert saved_outbox.event_type == "ConversationCreated"


def test_mssql_uow_atomic_rollback_on_exception(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)
    uow = MssqlUnitOfWork(session_factory=session_factory)

    conversation = Conversation.create(title="Integration UoW Rollback")
    outbox = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=conversation.id,
        event_type="ConversationCreated",
        payload="{}",
    )

    with pytest.raises(RuntimeError, match="Simulated crash"):
        with uow:
            uow.conversations.add(conversation)
            uow.outbox.save(outbox)
            raise RuntimeError("Simulated crash")

    with session_factory() as session:
        saved_conv = session.get(ConversationModel, conversation.id)
        saved_outbox = session.get(OutboxMessageModel, outbox.id)

        assert saved_conv is None
        assert saved_outbox is None


def test_mssql_uow_explicit_rollback(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)
    uow = MssqlUnitOfWork(session_factory=session_factory)

    conversation = Conversation.create(title="Explicit Rollback")

    with uow:
        uow.conversations.add(conversation)
        uow.rollback()

    with session_factory() as session:
        saved_conv = session.get(ConversationModel, conversation.id)
        assert saved_conv is None


def test_mssql_uow_auto_persists_outbox_events_atomically(
    mssql_engine: Engine, clean_db: None
) -> None:
    session_factory = create_session_factory(mssql_engine)
    uow = MssqlUnitOfWork(session_factory=session_factory)

    conversation = Conversation.create(title="Auto Outbox Persist")
    conversation.append_user_message("Test message for auto outbox")

    with uow:
        # Note: we ONLY add the conversation; outbox events must be automatically drained and saved
        uow.conversations.add(conversation)
        uow.commit()

    with session_factory() as session:
        outbox_records = session.exec(
            select(OutboxMessageModel).order_by(OutboxMessageModel.created_at)  # type: ignore[arg-type]
        ).all()
        assert len(outbox_records) == 2
        assert outbox_records[0].event_type == "ConversationCreatedDomainEvent"
        assert outbox_records[1].event_type == "MessageAppendedDomainEvent"
        assert outbox_records[0].status == "pending"
        assert outbox_records[1].status == "pending"
