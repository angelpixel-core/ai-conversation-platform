"""
Template canónico para Pruebas de Integración de Adaptador de Persistencia In-Memory.
Reglas:
- Verifica guardado, recuperación por ID, aislamiento transaccional y limpiezas.
"""

from uuid import uuid4

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.domain.conversations.entities.conversation import Conversation


def test_in_memory_repository_save_and_find() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create(title="Repo Test")

    # Act
    uow.repository.save(conversation)
    retrieved = uow.repository.get_by_id(conversation.id)

    # Assert
    assert retrieved is not None
    assert retrieved.id == conversation.id
    assert retrieved.title == "Repo Test"


def test_in_memory_repository_returns_none_for_missing() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()

    # Act & Assert
    assert uow.repository.get_by_id(uuid4()) is None
