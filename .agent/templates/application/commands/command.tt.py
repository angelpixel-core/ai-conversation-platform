# .agent/templates/command-handlers/python/command.template.py
"""
Template canónico para un Command DTO en Python.
Reglas:
- Inmutable (frozen dataclass).
- Tipos nativos o primitivos.
- Sin lógica de negocio.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateExampleCommand:
    name: str
    custom_id: Optional[UUID] = None
