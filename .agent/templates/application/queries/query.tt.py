# .agent/templates/query-handlers/python/query.template.py
"""
Template canónico para un Query DTO en Python.
Reglas:
- Inmutable (frozen dataclass).
- Parámetros de filtrado, paginación o identificadores.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetExampleByIdQuery:
    entity_id: UUID
