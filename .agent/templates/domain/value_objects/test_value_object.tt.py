"""
Template canónico para Pruebas Unitarias de Value Objects (DDD).
Reglas:
- Verifica inmutabilidad, igualdad estructural y validación estricta de invariantes de negocio.
"""

from datetime import datetime, timezone
import pytest

from .value_object import MessageValueObject, MessageRole


def test_value_object_creation_and_immutability() -> None:
    # Arrange & Act
    msg = MessageValueObject.create_user_message("Hola, asistente IA.")

    # Assert
    assert msg.role == MessageRole.USER
    assert msg.content == "Hola, asistente IA."
    assert msg.created_at.tzinfo is not None

    # Probar inmutabilidad (@dataclass(frozen=True))
    with pytest.raises(AttributeError):
        msg.content = "Intento de mutación"  # type: ignore[misc]


def test_value_object_equality_by_value() -> None:
    # Arrange
    now = datetime.now(timezone.utc)
    msg1 = MessageValueObject(role=MessageRole.USER, content="Test", created_at=now)
    msg2 = MessageValueObject(role=MessageRole.USER, content="Test", created_at=now)

    # Assert (dos VOs con los mismos atributos son estructuralmente iguales)
    assert msg1 == msg2


def test_value_object_validates_empty_content() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="no puede estar vacío"):
        MessageValueObject.create_user_message("   ")
