"""
Template canónico para Pruebas Unitarias de Command Handlers (TDD).
Reglas:
- Prueba la orquestación del handler en aislamiento inyectando repositorios in-memory y UnitOfWork.
- Verifica la mutación de estado, la transacción atómica y la generación de eventos.
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
    uow = InMemoryUnitOfWork()
    handler = CreateConversationHandler(unit_of_work=uow)
    command = CreateConversationCommand(title="Prueba Command Handler")

    # Act
    result = handler.handle(command)

    # Assert
    assert result.conversation_id is not None
    assert result.title == "Prueba Command Handler"
    assert uow.repository.get_by_id(result.conversation_id) is not None


def test_create_conversation_handler_raises_error_on_invalid_input() -> None:
    # Arrange
    uow = InMemoryUnitOfWork()
    handler = CreateConversationHandler(unit_of_work=uow)
    command = CreateConversationCommand(title="   ")

    # Act & Assert
    with pytest.raises(ValueError, match="no puede estar vacío"):
        handler.handle(command)
