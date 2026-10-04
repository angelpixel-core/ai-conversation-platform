"""MSSQL Conversation Repository adapter using SQLModel and Transactional Outbox."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.persistence.mssql.mapper import ConversationDataMapper
from src.infrastructure.persistence.mssql.models import ConversationModel, OutboxMessageModel
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxStatus


class MssqlConversationRepository(ConversationRepository):
    """Relational persistence adapter implementing the ConversationRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, conversation: Conversation) -> None:
        """Persist or synchronize a Conversation aggregate in the database session.

        Does not perform commit; transaction boundary is controlled by the Unit of Work.
        """
        existing = self._session.get(ConversationModel, conversation.id)
        target_model: ConversationModel
        if existing is None:
            target_model = ConversationDataMapper.to_model(conversation)
            self._session.add(target_model)
        else:
            target_model = existing
            target_model.title = conversation.title
            target_model.updated_at = datetime.now(UTC)

            # Synchronize new messages (messages are append-only Value Objects)
            existing_count = len(target_model.messages)
            new_messages = conversation.messages[existing_count:]
            for msg in new_messages:
                msg_model = ConversationDataMapper.message_to_model(
                    msg, conversation_id=conversation.id
                )
                self._session.add(msg_model)

        # Synchronize and drain domain events to the outbox table within the same transaction
        current_tenant = (
            get_current_tenant_id() or getattr(target_model, "tenant_id", None) or "default-tenant"
        )
        for event in conversation.pull_events():
            envelope = EventEnvelope.from_domain_event(event)
            envelope_dict = envelope.to_dict()
            if (
                isinstance(envelope_dict.get("payload"), dict)
                and "tenant_id" not in envelope_dict["payload"]
            ):
                envelope_dict["payload"]["tenant_id"] = current_tenant
            outbox_model = OutboxMessageModel(
                id=envelope.id,
                event_type=type(event).__name__,
                payload=json.dumps(envelope_dict),
                status=OutboxStatus.PENDING.value,
                created_at=envelope.occurred_on,
            )
            self._session.add(outbox_model)

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


# Canonical adapter alias conforming to <Technology><Port>Adapter
MssqlConversationRepositoryAdapter = MssqlConversationRepository
