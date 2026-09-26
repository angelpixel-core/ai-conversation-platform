"""Template canónico para Data Mappers en Clean Architecture.

Reglas:
- Pertenece a la capa de Infraestructura (src/infrastructure/persistence/.../mappers/).
- Convierte bidireccionalmente entre Entidades del Dominio y Modelos Relacionales SQLModel.
- Reconstituye Agregados completos con sus Value Objects y listas internas sin bypass de reglas.
"""

from uuid import UUID

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.message import Message, MessageRole
from .models import ConversationModel, MessageModel


class ConversationDataMapper:
    """Mapeador de datos entre la entidad Conversation y el modelo relacional ConversationModel."""

    @staticmethod
    def to_domain(model: ConversationModel) -> Conversation:
        """Reconstituye el Aggregate Root Conversation a partir del modelo de base de datos."""
        messages: list[Message] = []
        for msg_model in model.messages:
            messages.append(
                Message(
                    role=MessageRole(msg_model.role),
                    content=msg_model.content,
                    created_at=msg_model.created_at,
                )
            )

        conversation = Conversation.reconstitute(
            conversation_id=model.id,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
            messages=messages,
        )
        return conversation

    @staticmethod
    def to_model(entity: Conversation) -> ConversationModel:
        """Convierte una entidad Conversation a su representación relacional ConversationModel."""
        model = ConversationModel(
            id=entity.id,
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        model.messages = [
            ConversationDataMapper.message_to_model(msg, conversation_id=entity.id)
            for msg in entity.messages
        ]
        return model

    @staticmethod
    def message_to_model(message: Message, conversation_id: UUID) -> MessageModel:
        """Convierte un Value Object Message a un registro de mensaje MessageModel."""
        return MessageModel(
            conversation_id=conversation_id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
        )
