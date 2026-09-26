"""Integration tests for MssqlConversationRepository against live SQL Server 2022."""

from uuid import uuid4

from sqlalchemy.engine import Engine

from src.domain.conversations.entities.conversation import Conversation
from src.infrastructure.persistence.mssql.connection import create_session_factory
from src.infrastructure.persistence.mssql.repository import MssqlConversationRepository


def test_mssql_repo_save_and_retrieve_with_messages(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)

    # 1. Create domain aggregate
    conversation = Conversation.create(title="Integration Conversation")
    conversation.append_user_message("Hello from integration test")
    conversation.append_assistant_message("Hello back from SQL Server")

    # 2. Persist in first transaction
    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    # 3. Retrieve in a completely new session
    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        retrieved = repo.get(conversation.id)

        assert retrieved is not None
        assert retrieved.id == conversation.id
        assert retrieved.title == "Integration Conversation"
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0].content == "Hello from integration test"
        assert retrieved.messages[0].role.value == "user"
        assert retrieved.messages[1].content == "Hello back from SQL Server"
        assert retrieved.messages[1].role.value == "assistant"


def test_mssql_repo_update_conversation_and_append_messages(
    mssql_engine: Engine, clean_db: None
) -> None:
    session_factory = create_session_factory(mssql_engine)

    conversation = Conversation.create(title="Initial Version")
    conversation.append_user_message("First Turn")

    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    # Mutate aggregate: append new turn and update title
    conversation.title = "Updated Version"
    conversation.append_assistant_message("Assistant Turn")

    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        retrieved = repo.get(conversation.id)

        assert retrieved is not None
        assert retrieved.title == "Updated Version"
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0].content == "First Turn"
        assert retrieved.messages[1].content == "Assistant Turn"


def test_mssql_repo_list_conversations(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)

    conv1 = Conversation.create(title="Conversation Alpha")
    conv2 = Conversation.create(title="Conversation Beta")

    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        repo.add(conv1)
        repo.add(conv2)
        session.commit()

    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        conversations = repo.list()
        assert len(conversations) == 2
        titles = [c.title for c in conversations]
        assert "Conversation Alpha" in titles
        assert "Conversation Beta" in titles


def test_mssql_repo_get_nonexistent_returns_none(mssql_engine: Engine, clean_db: None) -> None:
    session_factory = create_session_factory(mssql_engine)

    with session_factory() as session:
        repo = MssqlConversationRepository(session=session)
        assert repo.get(uuid4()) is None
