"""Unit tests for MSSQL SQLModel models and ConversationMapper."""

from datetime import UTC, datetime
from uuid import uuid4

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.message import Message, MessageRole
from src.infrastructure.persistence.mssql.mapper import ConversationMapper
from src.infrastructure.persistence.mssql.models import (
    ConversationModel,
    MessageModel,
    OutboxMessageModel,
)


def test_mapper__entity_to_model__converts_conversation_and_messages_correctly() -> None:
    # Arrange
    conversation = Conversation.create(title="Arquitectura Limpia con MSSQL")
    conversation.append_user_message("¿Cómo persistir en SQL Server?")
    conversation.append_assistant_message("Utilizando Data Mappers y SQLModel.")

    # Act
    model = ConversationMapper.to_model(conversation)

    # Assert
    assert isinstance(model, ConversationModel)
    assert model.id == conversation.id
    assert model.title == "Arquitectura Limpia con MSSQL"
    assert model.created_at == conversation.created_at
    assert len(model.messages) == 2

    first_msg = model.messages[0]
    assert first_msg.role == "user"
    assert first_msg.content == "¿Cómo persistir en SQL Server?"
    assert first_msg.conversation_id == conversation.id

    second_msg = model.messages[1]
    assert second_msg.role == "assistant"
    assert second_msg.content == "Utilizando Data Mappers y SQLModel."
    assert second_msg.conversation_id == conversation.id


def test_mapper__model_to_domain__reconstitutes_aggregate_with_messages_correctly() -> None:
    # Arrange
    conv_id = uuid4()
    now = datetime.now(UTC)
    model = ConversationModel(
        id=conv_id,
        title="Reconstituted MSSQL Chat",
        created_at=now,
        updated_at=now,
    )
    model.messages = [
        MessageModel(
            id=uuid4(),
            conversation_id=conv_id,
            role="user",
            content="Mensaje histórico 1",
            created_at=now,
        ),
        MessageModel(
            id=uuid4(),
            conversation_id=conv_id,
            role="assistant",
            content="Respuesta histórica 2",
            created_at=now,
        ),
    ]

    # Act
    entity = ConversationMapper.to_domain(model)

    # Assert
    assert isinstance(entity, Conversation)
    assert entity.id == conv_id
    assert entity.title == "Reconstituted MSSQL Chat"
    assert entity.created_at == now
    assert len(entity.messages) == 2
    assert entity.messages[0].role == MessageRole.USER
    assert entity.messages[0].content == "Mensaje histórico 1"
    assert entity.messages[1].role == MessageRole.ASSISTANT
    assert entity.messages[1].content == "Respuesta histórica 2"


def test_mapper__message_to_model__converts_single_message_value_object() -> None:
    # Arrange
    conv_id = uuid4()
    message = Message.create_user_message("Prueba unitaria de Value Object")

    # Act
    model = ConversationMapper.message_to_model(message, conversation_id=conv_id)

    # Assert
    assert isinstance(model, MessageModel)
    assert model.conversation_id == conv_id
    assert model.role == "user"
    assert model.content == "Prueba unitaria de Value Object"
    assert model.created_at == message.created_at


def test_outbox_message_model__defaults_and_fields() -> None:
    # Arrange
    outbox_id = uuid4()

    # Act
    outbox = OutboxMessageModel(
        id=outbox_id,
        event_type="MessageAppendedDomainEvent",
        payload='{"conversation_id": "123"}',
    )

    # Assert
    assert outbox.id == outbox_id
    assert outbox.event_type == "MessageAppendedDomainEvent"
    assert outbox.payload == '{"conversation_id": "123"}'
    assert outbox.status == "pending"
    assert outbox.processed_at is None
    assert outbox.error_message is None
    assert isinstance(outbox.created_at, datetime)
