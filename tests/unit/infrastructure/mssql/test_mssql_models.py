"""Unit tests for MSSQL physical database models."""

from collections.abc import Iterator
from datetime import datetime
from uuid import uuid4

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.infrastructure.persistence.mssql.models import (
    AuditLogModel,
    ConversationModel,
    IdempotencyRecordModel,
    MessageModel,
    OutboxMessageModel,
    StreamBufferChunkModel,
)


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_conversation_and_message_models_relationship(sqlite_session: Session) -> None:
    conv_id = uuid4()
    conversation = ConversationModel(id=conv_id, title="Test Conversation")
    message = MessageModel(
        conversation_id=conv_id,
        role="user",
        content="Hello world",
    )
    conversation.messages.append(message)
    sqlite_session.add(conversation)
    sqlite_session.commit()

    saved = sqlite_session.get(ConversationModel, conv_id)
    assert saved is not None
    assert saved.title == "Test Conversation"
    assert len(saved.messages) == 1
    assert saved.messages[0].role == "user"
    assert saved.messages[0].content == "Hello world"


def test_outbox_message_model_defaults_and_creation(sqlite_session: Session) -> None:
    msg_id = uuid4()
    outbox = OutboxMessageModel(
        id=msg_id,
        event_type="ConversationCreated",
        payload='{"title": "Test"}',
    )
    sqlite_session.add(outbox)
    sqlite_session.commit()

    saved = sqlite_session.get(OutboxMessageModel, msg_id)
    assert saved is not None
    assert saved.status == "pending"
    assert saved.processed_at is None
    assert saved.error_message is None
    assert isinstance(saved.created_at, datetime)


def test_idempotency_record_model_creation_and_defaults(sqlite_session: Session) -> None:
    rec = IdempotencyRecordModel(
        key="test-key-123",
        status="pending",
    )
    sqlite_session.add(rec)
    sqlite_session.commit()

    saved = sqlite_session.exec(
        select(IdempotencyRecordModel).where(IdempotencyRecordModel.key == "test-key-123")
    ).first()
    assert saved is not None
    assert saved.key == "test-key-123"
    assert saved.status == "pending"
    assert saved.response_code is None
    assert saved.response_body is None
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


def test_audit_log_model_creation_and_defaults(sqlite_session: Session) -> None:
    audit_id = uuid4()
    audit = AuditLogModel(
        id=audit_id,
        event_name="llm_inference",
        actor_id="user-42",
        resource_type="chat",
        resource_id="chat-99",
        action="inference",
        tokens_consumed=150,
        payload_json='{"model": "gpt-4"}',
    )
    sqlite_session.add(audit)
    sqlite_session.commit()

    saved = sqlite_session.get(AuditLogModel, audit_id)
    assert saved is not None
    assert saved.event_name == "llm_inference"
    assert saved.actor_id == "user-42"
    assert saved.tokens_consumed == 150
    assert saved.payload_json == '{"model": "gpt-4"}'
    assert isinstance(saved.occurred_at, datetime)


def test_stream_buffer_chunk_model_creation_and_defaults(sqlite_session: Session) -> None:
    chunk_id = str(uuid4())
    chunk = StreamBufferChunkModel(
        id=chunk_id,
        stream_id="stream-xyz",
        sequence_number=3,
        content="world",
        is_final=True,
    )
    sqlite_session.add(chunk)
    sqlite_session.commit()

    saved = sqlite_session.get(StreamBufferChunkModel, chunk_id)
    assert saved is not None
    assert saved.stream_id == "stream-xyz"
    assert saved.sequence_number == 3
    assert saved.content == "world"
    assert saved.is_final is True
    assert isinstance(saved.created_at, datetime)
