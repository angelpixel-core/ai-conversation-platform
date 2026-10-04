"""Data mapper between Conversation aggregate root and MSSQL physical models."""

from uuid import UUID

from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.message import Message, MessageRole
from src.infrastructure.persistence.mssql.models import ConversationModel, MessageModel


class ConversationMapper:
    """Bidirectional data mapper between domain entities and SQLModel database models."""

    @staticmethod
    def to_domain(model: ConversationModel) -> Conversation:
        """Reconstitute Conversation aggregate root from SQLModel database model."""
        messages: list[Message] = []
        sorted_models = sorted(model.messages, key=lambda m: m.created_at)
        for msg_model in sorted_models:
            messages.append(
                Message(
                    role=MessageRole(msg_model.role),
                    content=msg_model.content,
                    created_at=msg_model.created_at,
                )
            )

        return Conversation.reconstitute(
            conversation_id=model.id,
            title=model.title,
            created_at=model.created_at,
            messages=messages,
        )

    @staticmethod
    def to_model(entity: Conversation) -> ConversationModel:
        """Map Conversation aggregate root to SQLModel database model."""
        current_tenant = get_current_tenant_id() or "default-tenant"
        model = ConversationModel(
            id=entity.id,
            tenant_id=current_tenant,
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.created_at,
        )
        model.messages = [
            ConversationMapper.message_to_model(msg, conversation_id=entity.id)
            for msg in entity.messages
        ]
        return model

    @staticmethod
    def to_persistence(entity: Conversation) -> ConversationModel:
        """Map Conversation aggregate root to SQLModel database model for persistence."""
        return ConversationMapper.to_model(entity)

    @staticmethod
    def message_to_model(message: Message, conversation_id: UUID) -> MessageModel:
        """Map Message value object to MessageModel database record."""
        return MessageModel(
            conversation_id=conversation_id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
        )


__all__ = ["ConversationMapper"]
