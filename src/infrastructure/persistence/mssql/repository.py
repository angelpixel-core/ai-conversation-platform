"""MSSQL Conversation Repository adapter using SQLModel."""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from src.infrastructure.persistence.mssql.mapper import ConversationDataMapper
from src.infrastructure.persistence.mssql.models import ConversationModel


class MssqlConversationRepository(ConversationRepository):
    """Relational persistence adapter implementing the ConversationRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, conversation: Conversation) -> None:
        """Persist or synchronize a Conversation aggregate in the database session.

        Does not perform commit; transaction boundary is controlled by the Unit of Work.
        """
        existing = self._session.get(ConversationModel, conversation.id)
        if existing is None:
            model = ConversationDataMapper.to_model(conversation)
            self._session.add(model)
        else:
            existing.title = conversation.title
            existing.updated_at = datetime.now(UTC)

            # Synchronize new messages (messages are append-only Value Objects)
            existing_count = len(existing.messages)
            new_messages = conversation.messages[existing_count:]
            for msg in new_messages:
                msg_model = ConversationDataMapper.message_to_model(
                    msg, conversation_id=conversation.id
                )
                self._session.add(msg_model)

    def get(self, conversation_id: UUID) -> Conversation | None:
        """Retrieve a Conversation aggregate by its unique identifier."""
        statement = select(ConversationModel).where(ConversationModel.id == conversation_id)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return ConversationDataMapper.to_domain(result)

    def list(self) -> list[Conversation]:
        """List all conversations ordered by creation date."""
        statement = select(ConversationModel).order_by(ConversationModel.created_at)  # type: ignore[arg-type]
        results = self._session.exec(statement).all()
        return [ConversationDataMapper.to_domain(model) for model in results]
