"""Template canónico para Adaptador de Repositorio Relacional con SQLModel / SQLAlchemy.

Reglas:
- Implementa el puerto del dominio ConversationRepository.
- Utiliza Session de SQLModel / SQLAlchemy.
- Recibe y retorna Agregados de Dominio (usa ConversationDataMapper internamente).
- NO realiza commit; la delimitación de transacciones es responsabilidad del Unit of Work.
"""

from uuid import UUID
from sqlmodel import Session, select

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from .mapper import ConversationDataMapper
from .models import ConversationModel, MessageModel


class SqlModelConversationRepository(ConversationRepository):
    """Adaptador de persistencia relacional que implementa ConversationRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, conversation: Conversation) -> None:
        """Guarda o actualiza un agregado Conversation en la sesión relacional."""
        existing = self._session.get(ConversationModel, conversation.id)
        if existing is None:
            model = ConversationDataMapper.to_model(conversation)
            self._session.add(model)
        else:
            existing.title = conversation.title
            existing.updated_at = conversation.updated_at

            # Sincronizar mensajes nuevos
            existing_count = len(existing.messages)
            new_messages = conversation.messages[existing_count:]
            for msg in new_messages:
                msg_model = ConversationDataMapper.message_to_model(
                    msg, conversation_id=conversation.id
                )
                self._session.add(msg_model)

    def get(self, conversation_id: UUID) -> Conversation | None:
        """Obtiene un agregado Conversation por su identificador único."""
        statement = select(ConversationModel).where(ConversationModel.id == conversation_id)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return ConversationDataMapper.to_domain(result)
