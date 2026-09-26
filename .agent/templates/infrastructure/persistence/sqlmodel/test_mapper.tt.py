"""Template canónico para Pruebas Unitarias del Data Mapper.

Reglas:
- Verifica la fidelidad de la traducción de Entidad de Dominio a Modelo Relacional (to_model).
- Verifica la reconstitución del Agregado de Dominio a partir del Modelo Relacional (to_domain).
- Asegura que los Value Objects y listas internas conserven todos sus atributos.
"""

from datetime import datetime, timezone
from uuid import uuid4

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.message import Message, MessageRole
from .mapper import ConversationDataMapper
from .models import ConversationModel, MessageModel


def test_mapper_entity_to_model() -> None:
    conversation = Conversation.create(title="Mapper Test")
    conversation.append_user_message("Hello from user")

    model = ConversationDataMapper.to_model(conversation)

    assert isinstance(model, ConversationModel)
    assert model.id == conversation.id
    assert model.title == "Mapper Test"
    assert len(model.messages) == 1
    assert model.messages[0].role == "user"
    assert model.messages[0].content == "Hello from user"
    assert model.messages[0].conversation_id == conversation.id


def test_mapper_model_to_domain() -> None:
    conv_id = uuid4()
    now = datetime.now(timezone.utc)
    model = ConversationModel(
        id=conv_id,
        title="Reconstituted Chat",
        created_at=now,
        updated_at=now,
    )
    model.messages = [
        MessageModel(
            conversation_id=conv_id,
            role="user",
            content="Message 1",
            created_at=now,
        )
    ]

    entity = ConversationDataMapper.to_domain(model)

    assert isinstance(entity, Conversation)
    assert entity.id == conv_id
    assert entity.title == "Reconstituted Chat"
    assert len(entity.messages) == 1
    assert entity.messages[0].role == MessageRole.USER
    assert entity.messages[0].content == "Message 1"
