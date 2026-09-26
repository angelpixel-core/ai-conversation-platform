"""
Template canónico para Pruebas Unitarias de Query Handlers (CQRS / Read Side).
Reglas:
- Verifica consultas de lectura y reconstrucción de Read Models o DTOs.
- No modifica estado ni ejecuta transacciones de escritura.
"""

from uuid import uuid4
import pytest

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.domain.conversations.entities.conversation import Conversation


def test_query_handler_returns_read_model_when_found() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create(title="Conversación de Lectura")
    uow.repository.save(conversation)

    # Act
    found = uow.repository.get_by_id(conversation.id)

    # Assert
    assert found is not None
    assert found.id == conversation.id
    assert found.title == "Conversación de Lectura"


def test_query_handler_returns_none_when_not_found() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()

    # Act
    found = uow.repository.get_by_id(uuid4())

    # Assert
    assert found is None
