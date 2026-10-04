"""Unit tests for MssqlConversationRepositoryAdapter adapter."""

import json
from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine, select

from src.domain.conversations.entities.conversation import Conversation
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.mssql.models import OutboxMessageModel
from src.infrastructure.persistence.mssql.repository import MssqlConversationRepositoryAdapter


def test_repository_add_and_get_conversation_without_messages() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conversation = Conversation.create(title="Empty Conversation")

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        retrieved = repo.get(conversation.id)

        assert retrieved is not None
        assert retrieved.id == conversation.id
        assert retrieved.title == "Empty Conversation"
        assert len(retrieved.messages) == 0


def test_repository_add_and_get_conversation_with_messages() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conversation = Conversation.create(title="Conversation With Messages")
    conversation.append_user_message("Hello from user")
    conversation.append_assistant_message("Hello back from assistant")

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        retrieved = repo.get(conversation.id)

        assert retrieved is not None
        assert retrieved.id == conversation.id
        assert retrieved.title == "Conversation With Messages"
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0].content == "Hello from user"
        assert retrieved.messages[0].role.value == "user"
        assert retrieved.messages[1].content == "Hello back from assistant"
        assert retrieved.messages[1].role.value == "assistant"


def test_repository_update_existing_conversation_and_append_new_messages() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conversation = Conversation.create(title="Initial Title")
    conversation.append_user_message("Message 1")

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        repo.add(conversation)
        session.commit()

    # Append new message and update title
    conversation.title = "Updated Title"
    conversation.append_assistant_message("Message 2")

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        retrieved = repo.get(conversation.id)

        assert retrieved is not None
        assert retrieved.title == "Updated Title"
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0].content == "Message 1"
        assert retrieved.messages[1].content == "Message 2"


def test_repository_get_nonexistent_returns_none() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        assert repo.get(uuid4()) is None


def test_repository_list_conversations() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conv1 = Conversation.create(title="First Conv")
    conv2 = Conversation.create(title="Second Conv")

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        repo.add(conv1)
        repo.add(conv2)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        all_convs = repo.list()
        assert len(all_convs) == 2
        titles = {c.title for c in all_convs}
        assert titles == {"First Conv", "Second Conv"}


def test_repository_add_automatically_drains_and_persists_domain_events_to_outbox() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conversation = Conversation.create(title="Outbox Drain Test")
    conversation.append_user_message("Hello transactional outbox")

    with Session(engine) as session:
        repo = MssqlConversationRepositoryAdapter(session=session)
        repo.add(conversation)
        session.commit()

    # The domain events on the aggregate should now be drained (empty)
    assert len(conversation.pull_events()) == 0

    # The outbox_messages table should contain the persisted events
    with Session(engine) as session:
        outbox_records = session.exec(
            select(OutboxMessageModel).order_by(OutboxMessageModel.created_at)  # type: ignore[arg-type]
        ).all()
        assert len(outbox_records) == 2
        assert outbox_records[0].event_type == "ConversationCreatedDomainEvent"
        assert outbox_records[1].event_type == "MessageAppendedDomainEvent"
        assert outbox_records[0].status == "pending"
        assert outbox_records[1].status == "pending"

        # Payloads should deserialize back to EventEnvelope
        payload_1 = json.loads(outbox_records[0].payload)
        env_1 = EventEnvelope.from_dict(payload_1)
        assert env_1.event_type == "conversation_created"
        assert env_1.payload["conversation_id"] == str(conversation.id)

        payload_2 = json.loads(outbox_records[1].payload)
        env_2 = EventEnvelope.from_dict(payload_2)
        assert env_2.event_type == "message_appended"
        assert env_2.payload["message"]["content"] == "Hello transactional outbox"
