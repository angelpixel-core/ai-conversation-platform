"""Canonical template: ToolDefinition Value Object."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable specification of an executable agent tool."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    is_deterministic: bool = True
    requires_approval: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre de la herramienta no puede estar vacío.")
        if not self.description.strip():
            raise ValueError("La descripción de la herramienta no puede estar vacía.")
        if not isinstance(self.parameters_schema, dict):
            raise ValueError("El parameters_schema debe ser un diccionario válido.")
