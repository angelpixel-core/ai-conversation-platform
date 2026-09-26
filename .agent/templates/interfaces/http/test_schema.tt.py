"""
Template canónico para Pruebas Unitarias de Esquemas Pydantic (DTOs HTTP).
Reglas:
- Verifica serialización/deserialización, aliases y validaciones de tipos.
"""

from uuid import uuid4
import pytest
from pydantic import ValidationError

from .schema import CreateExampleRequest, ExampleResponse


def test_schema_validates_and_serializes_correctly() -> None:
    req = CreateExampleRequest(title="Ejemplo DTO")
    assert req.title == "Ejemplo DTO"

    resp = ExampleResponse(id=uuid4(), title="Ejemplo DTO")
    assert resp.title == "Ejemplo DTO"


def test_schema_raises_validation_error_on_invalid_types() -> None:
    with pytest.raises(ValidationError):
        CreateExampleRequest.model_validate({"title": 12345})
