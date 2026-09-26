"""
Template canónico para Pruebas de Integración de Adaptadores de Infraestructura.
Reglas:
- Verifica la interacción con el sistema de persistencia in-memory o real.
- Garantiza la atomicidad de transacciones en la unidad de trabajo y el ciclo de vida del Outbox.
"""

from uuid import uuid4
import pytest

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.domain.conversations.entities.conversation import Conversation


def test_in_memory_repository_saves_and_retrieves_aggregate() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    conversation = Conversation.create(title="Test de Persistencia")

    # Act
    uow.repository.save(conversation)
    retrieved = uow.repository.get_by_id(conversation.id)

    # Assert
    assert retrieved is not None
    assert retrieved.id == conversation.id
    assert retrieved.title == "Test de Persistencia"
