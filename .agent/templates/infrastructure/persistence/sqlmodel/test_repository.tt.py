"""Template canónico para Pruebas del Repositorio Relacional con SQLModel.

Reglas:
- Verifica add y get de agregados Conversation.
- Verifica persistencia en cascada de nuevos mensajes añadidos al agregado.
- Retorna None si la conversación no existe.
"""

from uuid import uuid4
from sqlmodel import Session, SQLModel, create_engine

from src.domain.conversations.entities.conversation import Conversation
from .repository import SqlModelConversationRepository


def test_repository_add_and_get_conversation() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conversation = Conversation.create(title="Repo Test")
    conversation.append_user_message("First message")

    with Session(engine) as session:
        repo = SqlModelConversationRepository(session=session)
        repo.add(conversation)
        session.commit()

    with Session(engine) as session:
        repo = SqlModelConversationRepository(session=session)
        retrieved = repo.get(conversation.id)

        assert retrieved is not None
        assert retrieved.id == conversation.id
        assert retrieved.title == "Repo Test"
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "First message"


def test_repository_get_nonexistent_returns_none() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = SqlModelConversationRepository(session=session)
        assert repo.get(uuid4()) is None
