"""Unit tests for MssqlConversationRepository adapter."""

from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine

from src.domain.conversations.entities.conversation import Conversation
from src.infrastructure.persistence.mssql.repository import MssqlConversationRepository


def test_repository_add_and_get_conversation_without_messages() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conversation = Conversation.create(title="Empty Conversation")

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
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
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
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
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    # Append new message and update title
    conversation.title = "Updated Title"
    conversation.append_assistant_message("Message 2")

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
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
        repo = MssqlConversationRepository(session=session)
        assert repo.get(uuid4()) is None


def test_repository_list_conversations() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conv1 = Conversation.create(title="First Conv")
    conv2 = Conversation.create(title="Second Conv")

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conv1)
        repo.add(conv2)
        session.commit()

    with Session(engine) as session:
        repo = MssqlConversationRepository(session=session)
        all_convs = repo.list()
        assert len(all_convs) == 2
        titles = {c.title for c in all_convs}
        assert titles == {"First Conv", "Second Conv"}
