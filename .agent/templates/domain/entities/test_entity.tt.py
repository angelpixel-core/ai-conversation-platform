"""
Template canónico para Pruebas Unitarias del Dominio (Entities & Aggregate Roots).
Reglas:
- Prueba lógica de negocio pura, validación de invariantes y emisión de eventos de dominio.
- No utiliza I/O, base de datos ni frameworks externos.
"""

from uuid import uuid4
import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.events.conversation_created import ConversationCreatedDomainEvent


def test_create_conversation_aggregate_records_event() -> None:
    # Act
    conversation = Conversation.create(title="Conversación de Prueba")

    # Assert
    assert conversation.id is not None
    assert conversation.title == "Conversación de Prueba"
    events = conversation.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], ConversationCreatedDomainEvent)
    assert events[0].conversation_id == conversation.id


def test_create_conversation_aggregate_validates_title() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="no puede estar vacío"):
        Conversation.create(title="   ")
