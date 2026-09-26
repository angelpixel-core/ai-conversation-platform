"""Template canónico para Pruebas de Modelos Relacionales SQLModel.

Reglas:
- Verifica la correcta definición de atributos, campos nulos/no nulos y valores por defecto.
- Valida la relación uno-a-muchos entre ConversationModel y MessageModel.
- Valida campos del OutboxMessageModel.
"""

from datetime import datetime, timezone
from uuid import uuid4
from sqlmodel import Session, SQLModel, create_engine, select

from .models import ConversationModel, MessageModel, OutboxMessageModel


def test_conversation_and_message_models_relationship() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    conv_id = uuid4()
    with Session(engine) as session:
        conversation = ConversationModel(id=conv_id, title="Test Conversation")
        message = MessageModel(
            conversation_id=conv_id,
            role="user",
            content="Hello world",
        )
        conversation.messages.append(message)
        session.add(conversation)
        session.commit()

    with Session(engine) as session:
        saved = session.get(ConversationModel, conv_id)
        assert saved is not None
        assert saved.title == "Test Conversation"
        assert len(saved.messages) == 1
        assert saved.messages[0].role == "user"
        assert saved.messages[0].content == "Hello world"


def test_outbox_message_model_defaults_and_creation() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg_id = uuid4()
    with Session(engine) as session:
        outbox = OutboxMessageModel(
            id=msg_id,
            event_type="ConversationCreated",
            payload='{"title": "Test"}',
        )
        session.add(outbox)
        session.commit()

    with Session(engine) as session:
        saved = session.get(OutboxMessageModel, msg_id)
        assert saved is not None
        assert saved.status == "pending"
        assert saved.processed_at is None
        assert saved.error_message is None
        assert isinstance(saved.created_at, datetime)
