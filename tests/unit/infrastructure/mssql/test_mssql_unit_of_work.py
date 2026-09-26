"""Unit tests for MssqlUnitOfWork adapter."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.domain.conversations.entities.conversation import Conversation
from src.infrastructure.persistence.mssql.models import ConversationModel, OutboxMessageModel
from src.infrastructure.persistence.mssql.unit_of_work import MssqlUnitOfWork
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage


def test_unit_of_work_unstarted_access_raises_runtime_error() -> None:
    engine = create_engine("sqlite:///:memory:")
    uow = MssqlUnitOfWork(session_factory=lambda: Session(engine))

    with pytest.raises(RuntimeError, match="UnitOfWork has not been started"):
        _ = uow.conversations

    with pytest.raises(RuntimeError, match="UnitOfWork has not been started"):
        _ = uow.outbox


def test_unit_of_work_atomic_commit_persists_conversation_and_outbox() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    uow = MssqlUnitOfWork(session_factory=lambda: Session(engine))

    conversation = Conversation.create(title="UoW Commit Test")
    conversation.append_user_message("First message")
    outbox = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=conversation.id,
        event_type="ConversationCreated",
        payload='{"title": "UoW Commit Test"}',
    )

    with uow:
        uow.conversations.add(conversation)
        uow.outbox.save(outbox)
        uow.commit()

    with Session(engine) as session:
        saved_conv = session.get(ConversationModel, conversation.id)
        saved_outbox = session.get(OutboxMessageModel, outbox.id)

        assert saved_conv is not None
        assert saved_conv.title == "UoW Commit Test"
        assert len(saved_conv.messages) == 1
        assert saved_conv.messages[0].content == "First message"
        assert saved_outbox is not None
        assert saved_outbox.event_type == "ConversationCreated"


def test_unit_of_work_rollback_on_exception_discards_changes() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    uow = MssqlUnitOfWork(session_factory=lambda: Session(engine))

    conversation = Conversation.create(title="UoW Rollback Test")
    outbox = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=conversation.id,
        event_type="ConversationCreated",
        payload="{}",
    )

    with pytest.raises(ValueError, match="Simulated crash"):
        with uow:
            uow.conversations.add(conversation)
            uow.outbox.save(outbox)
            raise ValueError("Simulated crash")

    with Session(engine) as session:
        assert session.get(ConversationModel, conversation.id) is None
        assert session.get(OutboxMessageModel, outbox.id) is None


def test_unit_of_work_explicit_rollback() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    uow = MssqlUnitOfWork(session_factory=lambda: Session(engine))

    conversation = Conversation.create(title="Explicit Rollback")

    with uow:
        uow.conversations.add(conversation)
        uow.rollback()

    with Session(engine) as session:
        assert session.get(ConversationModel, conversation.id) is None


def test_unit_of_work_commit_and_rollback_outside_context_raises() -> None:
    engine = create_engine("sqlite:///:memory:")
    uow = MssqlUnitOfWork(session_factory=lambda: Session(engine))

    with pytest.raises(RuntimeError, match="Cannot commit: No active session"):
        uow.commit()

    with pytest.raises(RuntimeError, match="Cannot rollback: No active session"):
        uow.rollback()
