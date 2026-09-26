"""
Template canónico para Pruebas Unitarias de Command Handlers (TDD).
Reglas:
- Prueba la lógica del handler en aislamiento usando repositorios in-memory / mocks.
- Verifica mutaciones del agregado, invocación de la unidad de trabajo y generación de eventos.
"""

from uuid import uuid4
import pytest

from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationHandler,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


def test_create_conversation_handler_executes_successfully() -> None:
    # Arrange
    unit_of_work = InMemoryUnitOfWork()
    handler = CreateConversationHandler(unit_of_work=unit_of_work)
    command = CreateConversationCommand(title="Prueba de Handler")

    # Act
    result = handler.handle(command)

    # Assert
    assert result.conversation_id is not None
    assert result.title == "Prueba de Handler"
    assert unit_of_work.repository.get_by_id(result.conversation_id) is not None


def test_create_conversation_handler_raises_error_on_invalid_title() -> None:
    # Arrange
    unit_of_work = InMemoryUnitOfWork()
    handler = CreateConversationHandler(unit_of_work=unit_of_work)
    command = CreateConversationCommand(title="")

    # Act & Assert
    with pytest.raises(ValueError, match="no puede estar vacío"):
        handler.handle(command)
